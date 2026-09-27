import { describe, expect, it } from "vitest";

import { confusionAt, pointAt, prCurve, rates, rocCurve } from "./classification";

const y = [1, 0, 1, 0, 1, 0];
const p = [0.9, 0.8, 0.6, 0.4, 0.3, 0.1];

describe("confusionAt", () => {
  it("counts probability >= threshold as positive", () => {
    expect(confusionAt(y, p, 0.5)).toEqual({ tp: 2, fp: 1, fn: 1, tn: 2 });
    expect(confusionAt(y, p, 0.6)).toEqual({ tp: 2, fp: 1, fn: 1, tn: 2 });
    expect(confusionAt(y, p, 0.95)).toEqual({ tp: 0, fp: 0, fn: 3, tn: 3 });
    expect(confusionAt(y, p, 0)).toEqual({ tp: 3, fp: 3, fn: 0, tn: 0 });
  });

  it("derives rates without dividing by zero", () => {
    expect(rates({ tp: 2, fp: 1, fn: 1, tn: 2 })).toMatchObject({ precision: 2 / 3, recall: 2 / 3, fpr: 1 / 3 });
    expect(rates({ tp: 0, fp: 0, fn: 3, tn: 3 }).precision).toBeNull();
  });
});

describe("curves", () => {
  it("ROC runs from (0,0) to (1,1)", () => {
    const roc = rocCurve(y, p);
    expect(roc[0].slice(0, 2)).toEqual([0, 0]);
    expect(roc.at(-1)!.slice(0, 2)).toEqual([1, 1]);
    expect(roc.every((pt, i) => i === 0 || pt[0] >= roc[i - 1][0])).toBe(true);
  });

  it("PR recall rises from 0 to 1 and ends at the base rate", () => {
    const pr = prCurve(y, p);
    expect(pr[0]).toEqual([0, 1, 1]);
    expect(pr.at(-1)!.slice(0, 2)).toEqual([1, 0.5]);
  });

  it("tied scores form a single step", () => {
    expect(rocCurve([1, 0, 1], [0.5, 0.5, 0.2])).toHaveLength(3);
  });

  it("pointAt matches confusionAt at the same threshold", () => {
    const roc = rocCurve(y, p);
    const [fpr, tpr] = pointAt(roc, 0.5)!;
    const r = rates(confusionAt(y, p, 0.5));
    expect([fpr, tpr]).toEqual([r.fpr, r.recall]);
  });
});
