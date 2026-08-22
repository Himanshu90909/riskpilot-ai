/* Editorial Trust Layer: honest, reproducible Track 02 evidence surfaced in the guided demo. */
export const evaluationResults = {
  task: "Account Takeover Sentinel",
  dataset: {
    totalRecords: 100000,
    trainingRecords: 80000,
    heldOutRecords: 20000,
    positiveRate: 0.3576,
    seed: "index-locked deterministic generator v1",
  },
  detector: {
    type: "defense-only weighted signal detector",
    threshold: 24,
  },
  metrics: {
    precision: 0.9335,
    recall: 0.8897,
    f1: 0.9111,
    falsePositiveRate: 0.0353,
    falsePositiveCostInr: 81540,
    missedLossInr: 946800,
    matrix: {
      truePositive: 6363,
      falsePositive: 453,
      falseNegative: 789,
      trueNegative: 12395,
    },
  },
  costModel: {
    falsePositiveCostInr: 180,
    falseNegativeCostInr: 1200,
  },
} as const;

export const formatMetric = (value: number) => `${(value * 100).toFixed(2)}%`;
export const formatInr = (value: number) => `₹${value.toLocaleString("en-IN")}`;
