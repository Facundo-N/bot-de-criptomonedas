#!/usr/bin/env python3
"""
entrenar_oraculo_ml.py — Entrenamiento con DATOS REALES v2
====================================================================
Usa velas reales de Binance. Genera labels con R:R dinámico.
"""

import warnings, os, sys
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from binance.spot import Spot as Client
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
from sklearn.preprocessing import StandardScaler
import joblib

warnings.filterwarnings("ignore")
MODELO_PATH = "modelo_oraculo_rf.pkl"
RANDOM_STATE = 42
SIMBOLO = "BTCUSDT"; INTERVALO = "1h"

FEATURES_COLUMNS = [
    "sma_accion","ema_accion","rsi_accion","bollinger_accion","adx_accion","supertrend_accion",
    "sma_confianza","ema_confianza","rsi_confianza","bollinger_confianza","adx_confianza","supertrend_confianza",
    "regimen_idx","adx_valor","volatilidad_zscore","precio_ema_ratio","rsi_valor",
]

def descargar_velas(dias=90):
    print(f"  📡 Descargando {dias} días...")
    try:
        cli = Client()
        fin = datetime.now()
        ini = fin - timedelta(days=dias)
        ks = cli.klines(symbol=SIMBOLO, interval=INTERVALO,
                        startTime=int(ini.timestamp()*1000),
                        endTime=int(fin.timestamp()*1000), limit=1000)
        if not ks or len(ks) < 100:
            ini = fin - timedelta(days=dias*2)
            ks = cli.klines(symbol=SIMBOLO, interval=INTERVALO,
                            startTime=int(ini.timestamp()*1000),
                            endTime=int(fin.timestamp()*1000), limit=1000)
        if not ks or len(ks) < 100: return None
        df = pd.DataFrame(ks, columns=["openTime","open","high","low","close","volume",
                                        "closeTime","quoteVolume","trades","takerBuyBase","takerBuyQuote","ignore"])
        for c in ["open","high","low","close","volume"]: df[c] = pd.to_numeric(df[c], errors="coerce")
        df["openTime"] = pd.to_datetime(df["openTime"], unit="ms")
        df = df[["openTime","open","high","low","close","volume"]].copy()
        df.columns = ["Fecha/Hora","Apertura","Máximo","Mínimo","Cierre","Volumen"]
        print(f"  ✅ {len(df)} velas")
        return df
    except Exception as e: print(f"❌ {e}"); return None

def calcular_adx(df, p=14):
    try:
        h=df["Máximo"].values; l=df["Mínimo"].values; c=df["Cierre"].values; n=len(h)
        if n<p*2: return np.zeros(n)
        um=np.diff(h); dm=np.diff(l)
        hl=h[1:]-l[1:]; hc=np.abs(h[1:]-c[:-1]); lc=np.abs(l[1:]-c[:-1])
        tr=np.maximum(np.maximum(hl,hc),lc)
        pdm=np.where((um>dm)&(um>0),um,0); ndm=np.where((dm>um)&(dm>0),dm,0)
        a=1.0/p; ts=np.zeros(n-1); ps=np.zeros(n-1); ns=np.zeros(n-1)
        ts[p-1]=np.mean(tr[:p]); ps[p-1]=np.mean(pdm[:p]); ns[p-1]=np.mean(ndm[:p])
        for i in range(p,n-1):
            ts[i]=ts[i-1]+a*(tr[i]-ts[i-1]); ps[i]=ps[i-1]+a*(pdm[i]-ps[i-1]); ns[i]=ns[i-1]+a*(ndm[i]-ns[i-1])
        pdi=100*ps/np.where(ts==0,1e-10,ts); ndi=100*ns/np.where(ts==0,1e-10,ts)
        dx=100*np.abs(pdi-ndi)/np.where((pdi+ndi)==0,1e-10,pdi+ndi)
        ax=np.zeros(n-1); ax[p-1]=np.mean(dx[:p])
        for i in range(p,n-1): ax[i]=ax[i-1]+a*(dx[i]-ax[i-1])
        af=np.zeros(n); af[p:]=ax[p-1:]; return af
    except: return np.zeros(len(df))

def calc_rsi(c,p=14):
    d=np.diff(c); g=np.where(d>0,d,0); ls=np.where(d<0,-d,0)
    ag=np.zeros(len(c)); al=np.zeros(len(c)); ag[p]=np.mean(g[:p]); al[p]=np.mean(ls[:p])
    for i in range(p+1,len(c)): ag[i]=(ag[i-1]*13+g[i-1])/14; al[i]=(al[i-1]*13+ls[i-1])/14
    rs=ag/np.where(al==0,1e-10,al); return 100-100/(1+rs)

def vol_z(df,p=14):
    h=df["Máximo"].values; l=df["Mínimo"].values; c=df["Cierre"].values
    tr=np.maximum(np.maximum(h-l,np.abs(h-np.roll(c,1))),np.abs(l-np.roll(c,1))); tr[0]=h[0]-l[0]
    atr=pd.Series(tr).ewm(span=p,adjust=False).mean().values
    if len(atr)<p*2: return np.zeros(len(df))
    m=np.mean(atr[-p:]); s=np.std(atr[-p:])
    return (atr-m)/s if s>0 else np.zeros(len(df))

def generar_muestras(df):
    from estrategias.estrategia_medias import evaluar as e1
    from estrategias.estrategia_ema import evaluar as e2
    from estrategias.estrategia_rsi import evaluar as e3
    from estrategias.estrategia_bollinger import evaluar as e4
    from estrategias.estrategia_adx import evaluar as e5
    from estrategias.estrategia_supertrend import evaluar as e6
    from capa2_regimen_detector import detectar_regimen
    
    es = [(e1,"SMA Crossover (20/50)","Trend Following"),(e2,"EMA Crossover (9/21)","Trend Following"),
          (e3,"RSI 14 Oversold/Overbought","Mean Reversion"),(e4,"Bollinger Bands Bounce","Mean Reversion"),
          (e5,"ADX Trend Strength Filter","Breakout & Momentum"),(e6,"SuperTrend Indicator","Trend Following")]
    
    p=df["Cierre"].values; mx=df["Máximo"].values; mn=df["Mínimo"].values
    rsi=calc_rsi(p); vz=vol_z(df); adx=calcular_adx(df)
    muestras=[]; labels=[]; vi=150
    
    for i in range(vi, len(df)-12):
        dfi=df.iloc[:i+1]; pa=p[i]
        votos=[]
        for f,n,c in es:
            try: v=f(dfi); v["nombre"]=n; v["categoria"]=c; votos.append(v)
            except: pass
        if not votos: continue
        try: reg=detectar_regimen(dfi)
        except: continue
        
        regimen=reg['regimen'].split()[0]
        av=adx[i]; vz_val=vz[i] if i<len(vz) else 0; rsi_val=rsi[i] if i<len(rsi) else 50
        
        # Usar R:R 1:1 para tener más muestras (3% arriba o abajo)
        tp_price=pa*1.03; sl_price=pa*0.97
        hit_tp=False; hit_sl=False
        for j in range(i+1, min(i+12, len(df))):
            if mx[j]>=tp_price: hit_tp=True; break
            if mn[j]<=sl_price: hit_sl=True; break
        
        # Si no tocó nada en 12h, ver dirección: subió o bajó?
        if not hit_tp and not hit_sl:
            # Mirar precio de cierre después de 12h
            fut = min(i+11, len(df)-1)
            if p[fut] > pa * 1.005: hit_tp = True  # subió >0.5%
            elif p[fut] < pa * 0.995: hit_sl = True  # bajó >0.5%
            else: continue  # plano, descartar
        
        label = 1 if hit_tp else 0
        
        accs=[0.0]*6; confs=[0.0]*6
        for v in votos:
            n=v["nombre"].upper(); a=v["accion"]; c=float(v.get("confianza",0))
            va=1.0 if a=="BUY" else (-1.0 if a=="SELL" else 0.0)
            if "SMA" in n or "MEDIA" in n: idx=0
            elif "EMA" in n: idx=1
            elif "RSI" in n: idx=2
            elif "BOLL" in n: idx=3
            elif "ADX" in n: idx=4
            elif "SUPER" in n: idx=5
            else: continue
            accs[idx]=va; confs[idx]=c
        
        ri=0
        if "TENDENCIA" in regimen: ri=1
        elif "RANGO" in regimen: ri=2
        elif "VOLATIL" in regimen: ri=3
        
        muestras.append(accs+confs+[ri,float(av),float(vz_val),1.0,float(rsi_val)])
        labels.append(label)
    
    return np.array(muestras), np.array(labels)

def entrenar_modelo():
    print("="*55+"\n  🧠 ENTRENAMIENTO CON DATOS REALES v2\n"+"="*55)
    df=descargar_velas(90)
    if df is None: return None,None
    X,y=generar_muestras(df)
    if len(X)<100: print(f"❌ Solo {len(X)} muestras"); return None,None
    
    ne=y.sum(); nf=len(y)-ne
    print(f"\n  📊 {len(X)} muestras: Éxitos={ne}({ne/len(y)*100:.1f}%) Fracasos={nf}({nf/len(y)*100:.1f}%)")
    
    # Balancear con SMOTE manual (duplicar clase minoritaria)
    idx_exito=np.where(y==1)[0]; idx_fracaso=np.where(y==0)[0]
    if len(idx_exito)<len(idx_fracaso):
        mul=int(len(idx_fracaso)/len(idx_exito))-1
        extra_idx=np.random.choice(idx_exito,size=len(idx_exito)*mul,replace=True)
        X=np.vstack([X,X[extra_idx]])
        y=np.hstack([y,y[extra_idx]])
        print(f"  🔄 Balanceado: {len(X)} muestras ({y.sum()} éxitos, {len(y)-y.sum()} fracasos)")
    
    X_tr,X_te,y_tr,y_te=train_test_split(X,y,test_size=0.25,random_state=RANDOM_STATE,stratify=y)
    scaler=StandardScaler()
    X_tr_s=scaler.fit_transform(X_tr); X_te_s=scaler.transform(X_te)
    
    print("\n  Entrenando...")
    rf=RandomForestClassifier(n_estimators=300,max_depth=10,min_samples_split=8,
                              min_samples_leaf=4,class_weight="balanced",
                              random_state=RANDOM_STATE,n_jobs=-1,oob_score=True)
    rf.fit(X_tr_s,y_tr)
    
    y_pred=rf.predict(X_te_s); y_proba=rf.predict_proba(X_te_s)[:,1]
    acc=rf.score(X_te_s,y_te); roc=roc_auc_score(y_te,y_proba)
    print(f"\n  📊 Precisión: {acc:.3f} | ROC-AUC: {roc:.3f}")
    
    report=classification_report(y_te,y_pred,target_names=["Fracaso","Éxito"],output_dict=True,zero_division=0)
    for cn in ["Fracaso","Éxito"]:
        m=report[cn]; print(f"     {cn:10s} Prec:{m['precision']:.3f} Recall:{m['recall']:.3f} F1:{m['f1-score']:.3f}")
    
    tn,fp,fn,tp=confusion_matrix(y_te,y_pred).ravel()
    print(f"     MC: [{tn} {fp}; {fn} {tp}]")
    
    imp=rf.feature_importances_
    print(f"\n  Top features:")
    for n,i in sorted(zip(FEATURES_COLUMNS,imp),key=lambda x:x[1],reverse=True)[:5]:
        print(f"     {n:20s}: {i:.3f}")
    
    print(f"\n  💾 Guardando '{MODELO_PATH}'...")
    joblib.dump({"modelo":rf,"scaler":scaler,"features":FEATURES_COLUMNS,
                 "umbral_probabilidad":0.55,"n_muestras":len(X),
                 "precision_test":float(acc),"roc_auc_test":float(roc)},MODELO_PATH)
    print("  ✅ OK")
    return rf,scaler

def cargar_modelo(path=MODELO_PATH):
    if not os.path.isfile(path): return None
    try: return joblib.load(path)
    except: return None

def construir_vector_caracteristicas(votos, regimen_idx=0, adx_valor=0, volatilidad_zscore=0, precio_ema_ratio=1.0, rsi_valor=50):
    accs=[0]*6; confs=[0]*6
    mn={"SMA":0,"CROSSOVER":0,"MEDIA":0,"EMA":1,"RSI":2,"BOLLINGER":3,"ADX":4,"SUPERTREND":5,"SUPER TREND":5}
    for v in votos:
        n=v.get("nombre","").upper(); a=v.get("accion","HOLD"); c=float(v.get("confianza",0))
        idx=None
        for k,val in mn.items():
            if k in n: idx=val; break
        if idx is not None: accs[idx]=1.0 if a=="BUY" else (-1.0 if a=="SELL" else 0.0); confs[idx]=min(max(c,0),100)
    return accs+confs+[float(regimen_idx),float(adx_valor),float(volatilidad_zscore),float(precio_ema_ratio),float(rsi_valor)]

def predecir(md,fv):
    rf=md["modelo"]; sc=md["scaler"]; umb=md.get("umbral_probabilidad",0.55)
    X=np.array(fv).reshape(1,-1); Xs=sc.transform(X); proba=rf.predict_proba(Xs)[0,1]
    if proba>=umb: a="BUY"; c=int(proba*100)
    elif proba<=(1.0-umb): a="SELL"; c=int((1.0-proba)*100)
    else: a="HOLD"; c=int((1.0-abs(0.5-proba))*100)
    return {"accion":a,"probabilidad_exito":round(proba,4),"confianza":min(c,100),"umbral_aplicado":umb}

def test():
    md=cargar_modelo()
    if not md: print("⚠️ No hay modelo"); return
    print(f"✅ Precisión: {md.get('precision_test','N/A')}")
    for desc,vec in [("BUY",[1,1,0,0,1,1,80,75,30,25,65,70,1,35,0.5,1.01,45]),
                      ("SELL",[-1,-1,-1,-1,0,-1,70,65,80,60,20,55,2,15,-0.3,0.98,75]),
                      ("HOLD",[0,0,0,0,0,0,20,20,30,25,10,20,0,20,0.1,1.0,50])]:
        r=predecir(md,vec); print(f"     {desc:5s} → {r['accion']} (prob:{r['probabilidad_exito']:.1%})")

if __name__=="__main__":
    if len(sys.argv)>1 and sys.argv[1]=="--test": test()
    else: entrenar_modelo(); print("\nPost:"); test()