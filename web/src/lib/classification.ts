// Threshold maths for binary classifiers, computed in the browser from the
// validation labels and predicted probabilities (/api/models/validation-predictions).
// "Predicted positive" means probability >= threshold, as in src/models/train_baselines.py.

export interface Confusion {
  tn: number;
  fp: number;
  fn: number;
  tp: number;
}

/** [x, y, threshold]: one operating point on a curve. */
export type CurvePoint = [number, number, number];

export function confusionAt(yTrue: number[], proba: (number | null)[], threshold: number): Confusion {
  const cm = { tn: 0, fp: 0, fn: 0, tp: 0 };
  yTrue.forEach((y, i) => {
    const positive = (proba[i] ?? 0) >= threshold;
    if (y === 1) cm[positive ? "tp" : "fn"] += 1;
    else cm[positive ? "fp" : "tn"] += 1;
  });
  return cm;
}

export function rates(cm: Confusion) {
  const div = (a: number, b: number) => (b ? a / b : null);
  return {
    precision: div(cm.tp, cm.tp + cm.fp),
    recall: div(cm.tp, cm.tp + cm.fn),
    fpr: div(cm.fp, cm.fp + cm.tn),
    accuracy: div(cm.tp + cm.tn, cm.tp + cm.tn + cm.fp + cm.fn),
  };
}

/** Cumulative (fp, tp) counts at each distinct threshold, highest score first. */
function sweep(yTrue: number[], proba: (number | null)[]) {
  const order = yTrue.map((_, i) => i).sort((a, b) => (proba[b] ?? 0) - (proba[a] ?? 0));
  const steps: { threshold: number; tp: number; fp: number }[] = [];
  let tp = 0;
  let fp = 0;
  order.forEach((idx, k) => {
    if (yTrue[idx] === 1) tp += 1;
    else fp += 1;
    const score = proba[idx] ?? 0;
    const next = order[k + 1];
    if (next === undefined || (proba[next] ?? 0) !== score) steps.push({ threshold: score, tp, fp });
  });
  const positives = yTrue.filter((y) => y === 1).length;
  return { steps, positives, negatives: yTrue.length - positives };
}

/** ROC curve as [fpr, tpr, threshold], from (0, 0) to (1, 1). */
export function rocCurve(yTrue: number[], proba: (number | null)[]): CurvePoint[] {
  const { steps, positives, negatives } = sweep(yTrue, proba);
  const points: CurvePoint[] = [[0, 0, 1]];
  for (const s of steps) points.push([negatives ? s.fp / negatives : 0, positives ? s.tp / positives : 0, s.threshold]);
  return points;
}

/** Precision-recall curve as [recall, precision, threshold], recall rising from 0 to 1. */
export function prCurve(yTrue: number[], proba: (number | null)[]): CurvePoint[] {
  const { steps, positives } = sweep(yTrue, proba);
  const points: CurvePoint[] = [];
  for (const s of steps) {
    points.push([positives ? s.tp / positives : 0, s.tp / (s.tp + s.fp), s.threshold]);
  }
  // sklearn convention: the curve starts at recall 0 with precision 1
  if (points.length) points.unshift([0, 1, 1]);
  return points;
}

/** The curve point whose threshold is closest to (at or above) `threshold`. */
export function pointAt(curve: CurvePoint[], threshold: number): CurvePoint | undefined {
  let best: CurvePoint | undefined;
  for (const p of curve) if (p[2] >= threshold) best = p;
  return best ?? curve[0];
}
