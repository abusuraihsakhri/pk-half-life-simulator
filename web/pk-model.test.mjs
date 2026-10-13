import test from 'node:test';
import assert from 'node:assert/strict';
import { simulatePk } from './pk-model.mjs';
const near=(a,b)=>assert.ok(Math.abs(a-b)<1e-8,String(a)+' != '+String(b));
test('single-dose half-life and AUC',()=>{
  const x=simulatePk({dose:500,volume:40,halfLife:6,horizon:12,samples:3});
  near(x.points[0].concentration,12.5);
  near(x.points[1].concentration,6.25);
  near(x.points[2].concentration,3.125);
  near(x.summary.horizonAuc/x.summary.aucInf,.75);
});
test('repeated-dose peaks, troughs, and AUC',()=>{
  const x=simulatePk({dose:100,volume:20,halfLife:6,horizon:12,interval:6,samples:3});
  near(x.summary.accumulation,2);
  near(x.summary.peak,10);
  near(x.summary.trough,5);
  near(x.summary.endConcentration,8.75);
  near(x.summary.horizonAuc,(5/(Math.LN2/6))*1.25);
  assert.equal(x.summary.doses,3);
});
test('invalid inputs',()=>{
  for(const dose of [0,-1,Infinity,NaN])
    assert.throws(()=>simulatePk({dose,volume:20,halfLife:6,horizon:10}));
  assert.throws(()=>simulatePk({dose:100,volume:20,halfLife:6,horizon:10000,interval:.01}));
});
