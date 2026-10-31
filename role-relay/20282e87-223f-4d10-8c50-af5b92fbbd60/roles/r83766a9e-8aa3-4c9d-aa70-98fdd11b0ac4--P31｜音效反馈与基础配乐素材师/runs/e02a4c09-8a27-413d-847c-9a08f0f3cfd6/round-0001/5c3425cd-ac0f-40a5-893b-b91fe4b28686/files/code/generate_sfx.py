#!/usr/bin/env python3
"""Deterministically regenerate the isolated P31 procedural SFX source WAVs. Python stdlib only."""
import math, random, wave, struct
from pathlib import Path
SR=44100
def env(t,d,a=.008,r=.08):
    return min(1.0,t/max(a,1e-6))*min(1.0,max(0.0,(d-t)/max(r,1e-6)))
def tone(d,f,amp=.2,sweep=None,noise=0,seed=1,shape="sine",a=.01,r=.1):
    rng=random.Random(seed); out=[]; phase=0.0
    for i in range(int(SR*d)):
        t=i/SR; hz=(sweep[0]+(sweep[1]-sweep[0])*t/d) if sweep else f
        phase += 2*math.pi*hz/SR; s=math.sin(phase)
        if shape=="square": s=1.0 if s>=0 else -1.0
        elif shape=="triangle": s=2/math.pi*math.asin(s)
        out.append(amp*env(t,d,a,r)*(s+noise*(rng.random()*2-1)))
    return out
def mix(*xs):
    n=max(map(len,xs)); return [sum(x[i] if i<len(x) else 0 for x in xs) for i in range(n)]
def save(p,x):
    with wave.open(str(p),"wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(b"".join(struct.pack("<h",int(max(-1,min(1,v))*32767)) for v in x))
def main():
    out=Path(__file__).resolve().parents[1]/"audio"/"source"; out.mkdir(parents=True,exist_ok=True)
    clips={
      "card_flight_whoosh.wav":mix(tone(.42,400,.10,(900,180),.75,11,a=.01,r=.14),tone(.42,500,.07,(1200,240),.35,12,a=.02,r=.12)),
      "impact_hit.wav":mix(tone(.22,95,.50,(140,45),.12,21,"triangle",a=.002,r=.15),tone(.12,1800,.24,(2600,500),.65,22,a=.001,r=.07)),
      "shield_block.wav":mix(tone(.34,650,.22,a=.005,r=.18),tone(.34,1300,.08,a=.005,r=.20)),
      "heal_chime.wav":mix(tone(.48,660,.18,a=.01,r=.30),tone(.48,1320,.08,a=.015,r=.30)),
      "status_buff_spark.wav":mix(tone(.31,900,.12,(500,1500),seed=31,a=.004,r=.22),tone(.31,1800,.10,(900,2400),seed=32,a=.004,r=.18)),
      "victory_sting.wav":mix(tone(.72,523.25,.18,a=.02,r=.42),tone(.72,1046.5,.07,a=.03,r=.40)),
      "defeat_sting.wav":mix(tone(.72,392,.19,a=.02,r=.40),tone(.72,196,.08,(196,110),seed=41,a=.03,r=.42)),
      "reward_chime.wav":mix(tone(.40,784,.16,a=.008,r=.30),tone(.40,1568,.06,a=.01,r=.28)),
      "error_tick.wav":mix(tone(.16,210,.20,seed=51,shape="square",a=.002,r=.10),tone(.16,430,.08,seed=52,shape="triangle",a=.002,r=.08)),
      "ui_click.wav":tone(.055,1250,.22,shape="triangle",a=.001,r=.035)
    }
    for name,samples in clips.items(): save(out/name,samples)
if __name__=="__main__": main()
