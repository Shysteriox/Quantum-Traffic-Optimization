"""Render saved trial-zero traces. No independent cosmetic traffic simulation."""
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.animation import FuncAnimation, FFMpegWriter, PillowWriter
import imageio_ffmpeg
from real_city_sim import ROOT, FIG, CACHE, ADOPTION

def main():
    net=json.loads((CACHE/'Fremont.json').read_text()); trace=json.loads((ROOT/'animation_trace.json').read_text()); xy=np.array(net['nodes']); edges=net['edges']
    fig,axs=plt.subplots(1,2,figsize=(12.8,7.2),dpi=100); fig.subplots_adjust(left=.025,right=.975,bottom=.10,top=.79,wspace=.07); fig.patch.set_facecolor('#101b2c')
    title=fig.text(.5,.94,'FREMONT / SIGNAL STUDY',ha='center',color='white',fontsize=23,weight='bold')
    subtitle=fig.text(.5,.88,'',ha='center',color='#b8cce0',fontsize=12)
    fig.text(.5,.035,'Synthetic traffic | Classical simulated annealing | OSM contributors | Color: queued vehicles at downstream node',ha='center',color='#a8b8cc',fontsize=9)
    collections=[]; dots=[]; labels=[]
    for ax,c in zip(axs,['Fixed-Time','SA-QUBO']):
        ax.set_aspect('equal'); ax.set_axis_off(); ax.set_xlim(xy[:,0].min()-50,xy[:,0].max()+50); ax.set_ylim(xy[:,1].min()-50,xy[:,1].max()+50)
        lc=LineCollection([e[4] for e in edges],linewidths=2.3,cmap='RdYlGn_r',clim=(0,60)); ax.add_collection(lc); collections.append(lc)
        dots.append(ax.scatter(xy[:,0],xy[:,1],s=10,color='#a9e6db',alpha=.55,zorder=3)); labels.append(ax.text(.03,1.05,c,transform=ax.transAxes,color='white',fontsize=15,va='bottom'))
    def update(frame):
        year=2025+frame//48; t=frame%48; phase=t/47; bg=np.array([.045,.075,.13])+np.sin(np.pi*phase)*np.array([.035,.05,.07]); fig.patch.set_facecolor(bg)
        subtitle.set_text(f'{year}  /  {ADOPTION[year-2025]:.0%} QUBO adoption  /  {6+t//4:02d}:{(t%4)*15:02d}  /  {net["source"]}')
        for k,c in enumerate(['Fixed-Time','SA-QUBO']):
            r=trace[f'{year}_{c}'][t]; q=np.array(r['queue']); collections[k].set_array(np.array([q[e[1],e[2]] for e in edges])); dots[k].set_sizes(8+np.sqrt(q.sum(1))*9*(1+.15*np.sin(frame)))
            labels[k].set_text(f'{c}     {r["co2_kg"]:.1f} kg idle CO2')
        return collections+dots+labels+[subtitle]
    anim=FuncAnimation(fig,update,frames=288,interval=100,blit=False)
    matplotlib.rcParams['animation.ffmpeg_path']=imageio_ffmpeg.get_ffmpeg_exe()
    try: anim.save(FIG/'fremont_traffic_animation.mp4',writer=FFMpegWriter(fps=10,bitrate=2500,extra_args=['-pix_fmt','yuv420p']))
    except (OSError,RuntimeError): anim.save(FIG/'fremont_traffic_animation.gif',writer=PillowWriter(fps=10))
    update(287); fig.savefig(FIG/'animation_preview.png',dpi=150,facecolor=fig.get_facecolor()); print('Animation complete')
if __name__=='__main__': main()
