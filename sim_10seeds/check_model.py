"""Small algebra checks plus saved-run conservation and matched-demand checks."""
import itertools, json
import numpy as np
from real_city_sim import qubo, ROOT
for prev in itertools.product([0,1],repeat=3):
    prev=np.array(prev); eff=np.array([[3.,7.],[8.,2.],[1.,4.]])
    links=[(0,1,0),(1,2,1)]; Q=qubo(eff,prev,links)
    energies=[]
    for state in itertools.product([0,1],repeat=3):
        x=np.array(state); polynomial=sum(v*x[i]*x[j] for (i,j),v in Q.items())
        direct=sum(eff[:,1]*x+eff[:,0]*(1-x))+1.8*sum(x!=prev)-.45*(x[0]*x[1]+(1-x[1])*(1-x[2]))
        energies.append(direct-polynomial)
    assert np.ptp(energies)<1e-10
p=ROOT/'city_results.json'
if p.exists():
    rows=json.loads(p.read_text())['runs']; TRIALS=len({r['trial'] for r in rows}); assert len(rows)==5*6*3*TRIALS  # changed in the 10-seed copy: was len(rows)==270 (3 trials)
    for r in rows: assert abs(r['arrivals']-r['exited']-r['remaining'])<1e-4
    for city in {r['city'] for r in rows}:
        for year in range(2025,2031):
            for trial in range(TRIALS):
                group=[r for r in rows if (r['city'],r['year'],r['trial'])==(city,year,trial)]
                assert len({r['arrivals'] for r in group})==1
                if year<2027:
                    a=[r['co2_kg'] for r in group if r['controller']!='Local-Greedy']; assert a[0]==a[1]
print('PASS: QUBO algebra; when results exist, conservation, matched demand and zero-adoption equality')
