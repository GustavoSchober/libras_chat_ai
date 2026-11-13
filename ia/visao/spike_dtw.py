"""Spike de 12/11/2026: DTW sobre landmarks holísticos do V-LIBRASIL, deixando 1 vídeo de fora.

Roda na pasta que tem lm/*.npz (saída do extrair_landmarks.py); a amostra usada (30 sinais
sorteados, semente 7) está em spike_amostra.json. Resultado e conclusão em KNOWLEDGE/15.
"""
import numpy as np, glob, os, re, sys
from numba import njit

DEDOS=[(0,1,2,3,4),(0,5,6,7,8),(0,9,10,11,12),(0,13,14,15,16),(0,17,18,19,20)]
ESPELHO_POSE=[0,4,5,6,1,2,3,8,7,10,9,12,11,14,13,16,15,18,17,20,19,22,21,24,23,26,25,28,27,30,29,32,31]

def ang(u,w):
    c=(u*w).sum(-1)/(np.linalg.norm(u,axis=-1)*np.linalg.norm(w,axis=-1)+1e-9); return np.arccos(np.clip(c,-1,1))
def angulos(h):
    v=lambda a,b: h[:,b]-h[:,a]; out=[]
    for d in DEDOS:
        for k in range(3): out.append(ang(v(d[k],d[k+1]),v(d[k+1],d[k+2])))
    for a,b in [(1,2),(2,3),(3,4)]: out.append(ang(v(0,DEDOS[a][2]),v(0,DEDOS[b][2])))
    out.append(ang(v(1,2),v(5,6)))
    return np.stack(out,-1)/np.pi
def normal(h):
    n=np.cross(h[:,5]-h[:,0],h[:,17]-h[:,0]); return n/(np.linalg.norm(n,axis=-1,keepdims=True)+1e-9)
def interp(x):
    x=x.copy(); t=np.arange(len(x))
    for c in range(x.shape[1]):
        m=~np.isnan(x[:,c])
        if m.sum()==0: x[:,c]=0
        elif (~m).any(): x[~m,c]=np.interp(t[~m],t[m],x[m,c])
    return x

def feats(z, espelhar=False):
    asp=np.array([z['wh'][0]/z['wh'][1],1,z['wh'][0]/z['wh'][1]],np.float32)
    pose,E,D=z['pose']*asp,z['esq']*asp,z['dir']*asp
    if espelhar:
        for a in (pose,E,D): a[...,0]*=-1
        E,D=D,E; pose=pose[:,ESPELHO_POSE]
    om=np.nanmedian((pose[:,11]+pose[:,12])/2,0); esc=np.nanmedian(np.linalg.norm(pose[:,11,:2]-pose[:,12,:2],axis=-1))
    nariz=(np.nanmedian(pose[:,0],0)[:2]-om[:2])/esc
    y=np.fmin(interp((E[:,0,1:2]-om[1])/esc)[:,0],interp((D[:,0,1:2]-om[1])/esc)[:,0])
    idx=np.where(y<np.median(y[:5])-0.2)[0]
    if len(idx)<3: idx=np.arange(len(y))
    sl=slice(idx[0],idx[-1]+1); f={}
    for nome,h in (('E',E[sl]),('D',D[sl])):
        pres=~np.isnan(h[:,0,0])
        p=(h[:,0,:2]-om[:2])/esc; p[~pres]=np.nan
        p=interp(p) if pres.any() else np.tile([0,2.5],(len(p),1))
        f['traj'+nome]=p; f['loc'+nome]=p-nariz
        f['vel'+nome]=np.diff(p,axis=0,prepend=p[:1])*5
        a=angulos(h); a[~pres]=np.nan; f['forma'+nome]=interp(a)
        n=normal(h); n[~pres]=np.nan; f['ori'+nome]=interp(n)
    return {k:v[::2].astype(np.float64) for k,v in f.items()}

@njit(cache=True)
def dtw(a,b):
    n,m=len(a),len(b); C=np.full((n+1,m+1),np.inf); C[0,0]=0
    for i in range(1,n+1):
        for j in range(1,m+1):
            d=np.sqrt(((a[i-1]-b[j-1])**2).sum()); C[i,j]=d+min(C[i-1,j],C[i,j-1],C[i-1,j-1])
    return C[n,m]/(n+m)

def carregar(pasta='lm'):
    arqs=sorted(glob.glob(pasta+'/*.npz'))
    nomes=[re.match(r'(.+)_Articulador(\d)',os.path.basename(a)).group(1) for a in arqs]
    F=[feats(np.load(a)) for a in arqs]; FM=[feats(np.load(a),True) for a in arqs]
    return nomes,F,FM

def matriz(F,FM,usar,esc,espelho=True):
    vet=lambda f: np.concatenate([f[k+h]/esc[k] for k in usar for h in 'ED'],-1)
    V=[vet(f) for f in F]; VM=[vet(f) for f in FM]; N=len(V); D=np.full((N,N),np.inf)
    for i in range(N):
        for j in range(N):
            if i!=j: D[i,j]=min(dtw(V[i],V[j]),dtw(VM[i],V[j])) if espelho else dtw(V[i],V[j])
    return D

def metricas(D,nomes):
    N=len(nomes); sinais=sorted(set(nomes)); gen=[];imp=[]; top1=top3=0
    for i in range(N):
        ds={s:min(D[i,j] for j in range(N) if nomes[j]==s and j!=i) for s in sinais}
        ordem=sorted(ds,key=ds.get); top1+=ordem[0]==nomes[i]; top3+=nomes[i] in ordem[:3]
        for s,d in ds.items(): (gen if s==nomes[i] else imp).append(d)
    gen,imp=np.array(gen),np.array(imp); auc=np.mean([(g<imp).mean() for g in gen])
    eer=min((((gen>t).mean()+(imp<=t).mean())/2,abs((gen>t).mean()-(imp<=t).mean())) for t in np.sort(np.concatenate([gen,imp])))
    eer=min(np.sort(np.concatenate([gen,imp])),key=lambda t:abs((gen>t).mean()-(imp<=t).mean()))
    return top1/N, top3/N, auc, ((gen>eer).mean()+(imp<=eer).mean())/2

if __name__=='__main__':
    nomes,F,FM=carregar()
    esc={k:np.std(np.concatenate([x[k+h] for x in F for h in 'ED']))+1e-9 for k in ('traj','loc','forma','ori','vel')}
    for usar in (['traj','forma'],['loc','forma'],['loc','forma','ori'],['loc','forma','vel'],['loc','forma','ori','vel']):
        print(f"{'+'.join(usar):22s} top1 {{:5.1%}}  top3 {{:5.1%}}  AUC {{:.3f}}  EER {{:5.1%}}".format(*metricas(matriz(F,FM,usar,esc),nomes)), flush=True)
