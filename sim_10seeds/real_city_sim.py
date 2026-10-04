"""Exploratory road-topology queue model; classical SA, not quantum hardware."""
from pathlib import Path
import json, csv, time, platform, subprocess, sys
import numpy as np
import osmnx as ox
import neal
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parent
CACHE=ROOT/'osm_cache'; FIG=ROOT/'figures'
CITIES={'Fremont':(37.5485,-121.9886),'Delhi':(28.6139,77.2090),'Los Angeles':(34.0522,-118.2437),'Singapore':(1.3521,103.8198),'Oslo':(59.9139,10.7522)}
ADOPTION=[0,0,.2,.5,.8,1]
DT=30; STEPS=1440; REPORT=30; EXIT=.4
TRIALS=10  # changed from 3 for the 10-seed run; seeds for trials 0-2 are unchanged
SAMPLER=neal.SimulatedAnnealingSampler()

def network(city):
    CACHE.mkdir(exist_ok=True); p=CACHE/(city.replace(' ','_')+'.json')
    if p.exists(): return json.loads(p.read_text())
    ox.settings.use_cache=True; ox.settings.cache_folder=str(CACHE/'http'); ox.settings.requests_timeout=35; ox.settings.overpass_rate_limit=False
    try:
        graphpath=CACHE/(city.replace(' ','_')+'.graphml')
        if not graphpath.exists():
            code=("import osmnx as ox; ox.settings.use_cache=True; "
                  f"ox.settings.cache_folder={str(CACHE/'http')!r}; "
                  "ox.settings.requests_timeout=35; ox.settings.overpass_rate_limit=False; "
                  f"g=ox.graph_from_point({CITIES[city]!r},dist=500,network_type='drive',simplify=True); "
                  f"ox.save_graphml(g,{str(graphpath)!r})")
            subprocess.run([sys.executable,'-c',code],check=True,timeout=75,capture_output=True)
        g=ox.load_graphml(graphpath)
        g=ox.bearing.add_edge_bearings(g); ids=list(g.nodes); idx={u:i for i,u in enumerate(ids)}
        lat,lon=CITIES[city]; xy=[[(g.nodes[u]['x']-lon)*111320*np.cos(np.deg2rad(lat)),(g.nodes[u]['y']-lat)*111320] for u in ids]
        edges=[]
        for u,v,d in g.edges(data=True):
            if u==v: continue
            b=d['bearing']%180; axis=0 if b<=45 or b>=135 else 1
            geom=d.get('geometry'); pts=list(geom.coords) if geom is not None else [(g.nodes[u]['x'],g.nodes[u]['y']),(g.nodes[v]['x'],g.nodes[v]['y'])]
            pts=[[(x-lon)*111320*np.cos(np.deg2rad(lat)),(y-lat)*111320] for x,y in pts]
            edges.append([idx[u],idx[v],axis,float(d['length']),pts])
        if len(ids)<3 or not edges: raise ValueError('Insufficient road network')
        ox.save_graphml(g,CACHE/(city.replace(' ','_')+'.graphml'))
        result=dict(city=city,source='OpenStreetMap',nodes=xy,edges=edges,osm_ids=ids,download_date=time.strftime('%Y-%m-%d'),radius_m=500)
    except Exception as e:
        xy=[[c*200-400,r*200-400] for r in range(5) for c in range(5)]; edges=[]
        for i in range(25):
            for j in range(25):
                if abs(i//5-j//5)+abs(i%5-j%5)==1: edges.append([i,j,0 if i//5!=j//5 else 1,200,[xy[i],xy[j]]])
        result=dict(city=city,source='synthetic 5x5 grid',fallback_reason=str(e),nodes=xy,edges=edges,radius_m=500)
    p.write_text(json.dumps(result,indent=2)); return result

def qubo(eff,prev,links):
    # E=sum diagonal*x + sum upper triangular*x_i*x_j; constants omitted.
    n=len(prev); Q={(i,i):float(eff[i,1]-eff[i,0]+1.8*(1-2*prev[i])) for i in range(n)}
    for i,j,a in links:
        if a==1:
            Q[i,i]+=.45; Q[j,j]+=.45
        Q[i,j]=Q.get((i,j),0)-.45
    return Q

def simulate(net,year,controller,trial,trace=False):
    n=len(net['nodes']); seed=41000+list(CITIES).index(net['city'])*100+trial
    rng=np.random.default_rng(seed); solver=np.random.default_rng(seed+90000)
    # Identical exogenous arrivals for all controllers and nested adoption per trial.
    ordering=np.random.default_rng(seed+80000).permutation(n); active=ordering[:round(n*ADOPTION[year-2025])]
    outgoing=[[] for _ in range(n)]
    links=set()
    for i,j,a,length,_ in net['edges']:
        outgoing[i].append((j,a,max(1,int(np.ceil(length/(30/3.6)/DT)))))
        links.add((min(i,j),max(i,j),a))
    links=sorted(links); lag=max(e[2] for out in outgoing for e in out)+1
    transit=np.zeros((lag,n,2)); q=np.zeros((n,2)); prev=np.zeros(n,dtype=int)
    x=prev.copy(); arrivals=exits=delay=0.; co2=0.; frames=[]; runqueue=[]
    spatial=np.random.default_rng(seed+70000).uniform(.7,1.3,(n,2))
    for t in range(STEPS):
        slot=t%lag; q+=transit[slot]; transit[slot]=0
        # Synthetic demand, independent of supplied city-level reference values.
        interval=t/REPORT; envelope=.55+.9*np.exp(-.5*((interval-10)/6)**2)
        season=1.0  # Same representative season across years: isolate 2% demand growth.
        new=rng.poisson(.025*DT*envelope*spatial*(1.02**(year-2025))*season)
        q+=new; arrivals+=new.sum(); changed=np.zeros(n,dtype=bool)
        if t%2==0:
            fixed=np.full(n,(t//2)%2,dtype=int)
            if controller=='Fixed-Time': x=fixed
            elif controller=='Local-Greedy': x=(q[:,0]>=q[:,1]).astype(int)
            else:
                x=fixed.copy()
                if len(active):
                    Q=qubo(np.minimum(q, .45*60),prev,links)
                    # Substitute non-adopted fixed phases into the joint objective.
                    aset=set(active.tolist()); reduced={(i,i):Q[i,i] for i in active}
                    for (i,j),v in Q.items():
                        if i==j: continue
                        if i in aset and j in aset: reduced[i,j]=v
                        elif i in aset: reduced[i,i]+=v*x[j]
                        elif j in aset: reduced[j,j]+=v*x[i]
                    sample=SAMPLER.sample_qubo(reduced,num_reads=4,num_sweeps=40,seed=int(solver.integers(1,2**30))).first.sample
                    for i in active: x[i]=sample[i]
            changed=x!=prev; prev=x.copy()
        capacity=.45*(DT-3*changed)
        axis=1-x; served=np.minimum(q[np.arange(n),axis],capacity)
        q[np.arange(n),axis]-=served
        for i,amount in enumerate(served):
            if not outgoing[i]: exits+=amount; continue
            exits+=EXIT*amount; share=(1-EXIT)*amount/len(outgoing[i])
            for j,a,travel in outgoing[i]: transit[(t+travel)%lag,j,a]+=share
        # End-step rectangle integration: explicit discrete queue approximation.
        idle=q.sum()*DT; delay+=idle; co2+=idle/900*.038
        if (t+1)%REPORT==0:
            runqueue.append(float(q.sum()))
            if trace: frames.append(dict(queue=q.tolist(),co2_kg=float(co2),step=t+1))
    pending=float(q.sum()+transit.sum())
    assert abs(arrivals-exits-pending)<1e-6*max(1,arrivals), 'Vehicle conservation failed'
    mean_link=np.mean([e[3] for e in net['edges']]); ff=mean_link/(30/3.6)/EXIT
    result=dict(city=net['city'],year=year,controller=controller,trial=trial,seed=seed,adoption=ADOPTION[year-2025] if controller=='SA-QUBO' else None,arrivals=int(arrivals),exited=float(exits),remaining=pending,wait_seconds_per_injected_vehicle=float(delay/arrivals),delay_vehicle_seconds=float(delay),co2_kg=co2,nox_g=delay/900*.047,fuel_l=delay/900*.016,annual_co2_kg=co2*250,annual_nox_g=delay/900*.047*250,congestion_proxy_percent=100*delay/arrivals/ff,mean_freeflow_proxy_seconds=float(ff))
    return result,frames

def figures(data):
    rows=data['runs']; names=list(CITIES); display=[n+' (grid)' if data['networks'][n]['source']!='OpenStreetMap' else n for n in names]; colors=['#537b9e','#d59546','#39816a']
    plt.rcParams.update({'font.family':'serif','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'savefig.dpi':300})
    def vals(city,year,ctrl,key): return np.array([r[key] for r in rows if r['city']==city and r['year']==year and r['controller']==ctrl])
    fig,axs=plt.subplots(1,3,figsize=(15,5),layout='constrained')
    for ax,key,label,scale in zip(axs,['annual_co2_kg','annual_nox_g','wait_seconds_per_injected_vehicle'],['Annual idle CO2 (tonnes)','Annual idle NOx (kg)','Accrued delay / injected vehicle (s)'],[1000,1000,1]):
        for k,c in enumerate(['Fixed-Time','Local-Greedy','SA-QUBO']):
            v=np.array([vals(n,2030,c,key)/scale for n in names]); ax.bar(np.arange(5)+(k-1)*.25,v.mean(1),.25,yerr=v.std(1,ddof=1),capsize=2,color=colors[k],label=c)
        ax.set_xticks(range(5),display,rotation=25); ax.set_ylabel(label)
        for i,n in enumerate(names):
            a=vals(n,2030,'Fixed-Time',key).mean(); b=vals(n,2030,'SA-QUBO',key).mean(); ax.text(i,max(vals(n,2030,c,key).mean()/scale for c in ['Fixed-Time','Local-Greedy','SA-QUBO'])*1.1,f'{100*(1-b/a):+.1f}%',ha='center',fontsize=8)
        ax.margins(y=.24)
    axs[0].legend(fontsize=8); fig.suptitle('A | Matched 2030 demand - synthetic traffic on sampled road networks\nLabels: SA-QUBO reduction versus fixed; error bars: trial SD (n=3)'); fig.savefig(FIG/'figA_city_comparison.png'); plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,5),layout='constrained')
    for n in names:
        base=vals(n,2025,'Fixed-Time','co2_kg').mean(); line=None
        for c,style in [('Fixed-Time','--'),('SA-QUBO','-')]:
            y=[vals(n,y,c,'co2_kg').mean()/base for y in range(2025,2031)]; line,=ax.plot(range(2025,2031),y,style,color=line.get_color() if line else None,label=display[names.index(n)] if c=='Fixed-Time' else None)
    ax.axvspan(2027,2030,color='#39816a',alpha=.08); ax.set(ylabel='Idle CO2 / fixed 2025 baseline',title='B | Scenario trends (dashed: fixed; solid: SA-QUBO)',xticks=range(2025,2031)); ax.legend(ncol=3,fontsize=9); fig.savefig(FIG/'figB_yearly_trend.png'); plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,5),layout='constrained'); xx=np.array([22,46,28,19,22]); yy=np.array([vals(n,2025,'Fixed-Time','congestion_proxy_percent').mean() for n in names]); fit=np.polyfit(xx,yy,1); r2=1-np.sum((yy-np.polyval(fit,xx))**2)/np.sum((yy-yy.mean())**2)
    ax.scatter(xx,yy,color=colors[0]); ax.plot([18,48],np.polyval(fit,[18,48]),color=colors[0],alpha=.5)
    for n,x,y in zip(display,xx,yy): ax.annotate(n,(x,y),xytext=(5,6),textcoords='offset points',fontsize=9)
    ax.set(xlabel='Prompt-supplied TomTom values (%) - unverified',ylabel='Model delay / assumed free-flow proxy (%)',title=f'C | Exploratory comparison only; regression R² = {r2:.2f}\nDifferent spatial coverage and metrics: not validation'); ax.margins(.2); fig.savefig(FIG/'figC_validation.png'); plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(12,5),layout='constrained')
    dif=np.array([(vals(n,2030,'Fixed-Time','annual_co2_kg')-vals(n,2030,'SA-QUBO','annual_co2_kg'))/1000 for n in names]); axs[0].bar(display,dif.mean(1),yerr=dif.std(1,ddof=1),capsize=3,color=colors[2]); axs[0].axhline(0,color='gray',lw=.7); axs[0].set(ylabel='Annual idle CO2 avoided (tonnes)',title='Matched 2030 scenarios; paired trial SD'); axs[0].tick_params(axis='x',rotation=25)
    axs[1].axis('off'); axs[1].text(.04,.85,'PM2.5 and health effects\nare not estimated.',fontsize=20,va='top'); axs[1].text(.04,.52,'An idling model does not supply pollutant dispersion,\nbackground sources, population exposure, or\na concentration-response model.\n\nCO2 savings cannot be converted directly\nto PM2.5 reductions.',fontsize=12,va='top'); fig.suptitle('D | Emissions scenario and limits of health inference'); fig.savefig(FIG/'figD_health_impact.png'); plt.close(fig)
    return float(r2)

def main():
    FIG.mkdir(exist_ok=True); runs=[]; networks={}; traces={}
    for city in CITIES:
        net=network(city); networks[city]=net; print(city,net['source'],len(net['nodes']),'nodes',flush=True)
        for year in range(2025,2031):
            print(city,year,flush=True)
            for trial in range(TRIALS):
                for ctrl in ['Fixed-Time','Local-Greedy','SA-QUBO']:
                    r,tr=simulate(net,year,ctrl,trial,city=='Fremont' and trial==0 and ctrl!='Local-Greedy'); runs.append(r)
                    if tr: traces[f'{year}_{ctrl}']=tr
    data=dict(description='Exploratory classical SA-QUBO simulation; no quantum advantage or real-world validation established',parameters=dict(base_arrivals_per_axis_per_second=.025,service_vehicles_per_second=.45,switch_lost_seconds=3,exit_fraction=EXIT,freeflow_kph=30,annual_demand_growth=.02,season_multiplier=1.0,solver_reads=4,solver_sweeps=40),annual_multiplier=250,dt_seconds=DT,steps=STEPS,reporting_intervals=48,weights=dict(queue=1,sync=.45,switch=1.8),networks={n:{k:v for k,v in net.items() if k not in ['nodes','edges','osm_ids']} for n,net in networks.items()},runs=runs)
    (ROOT/'city_results.json').write_text(json.dumps(data,indent=2)); (ROOT/'animation_trace.json').write_text(json.dumps(traces))
    with (ROOT/'results.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=runs[0]); w.writeheader(); w.writerows(runs)
    r2=float('nan')  # figures() is not called in the 10-seed copy; the paper figures come from make_figures.py
    summary=['# Results from this run','', f'{TRIALS} paired trials per city/year/controller; {len(runs)} runs. Annual totals cover only each sampled network, using 250 twelve-hour days.','', '| City | Fixed CO2, 2030 (kg/run) | Greedy | SA-QUBO | SA reduction vs fixed |','|---|---:|---:|---:|---:|']
    for n in CITIES:
        v=[np.mean([r['co2_kg'] for r in runs if r['city']==n and r['year']==2030 and r['controller']==c]) for c in ['Fixed-Time','Local-Greedy','SA-QUBO']]; summary.append(f'| {n} | {v[0]:.2f} | {v[1]:.2f} | {v[2]:.2f} | {100*(1-v[2]/v[0]):.1f}% |')
    summary+=['','These results measure controller behavior under assumed demand, not observed city traffic. The greedy controller is an essential comparator; a benefit over fixed timing alone is not a quantum benefit.','',f'Exploratory reference scatter R²: {r2:.3f}. This is not a validation statistic for comparable measurements.']
    (ROOT/'RESULTS.md').write_text('\n'.join(summary)); print(f'Complete: {len(runs)} runs',flush=True)
if __name__=='__main__': main()
