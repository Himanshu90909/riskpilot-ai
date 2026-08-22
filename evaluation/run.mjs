/* RiskPilot Track 02: deterministic Account Takeover Sentinel evaluation. */

const TOTAL_RECORDS = 100000;
const TRAINING_RECORDS = 80000;
const HELD_OUT_RECORDS = TOTAL_RECORDS - TRAINING_RECORDS;
const FN_COST = 1200;
const FP_COST = 180;

function pseudo(seed) {
  const value = Math.sin(seed * 12.9898) * 43758.5453;
  return value - Math.floor(value);
}

function makeRecord(index) {
  const newDevice = pseudo(index + 11) > 0.82;
  const newLocation = pseudo(index + 17) > 0.86;
  const passwordReset = pseudo(index + 23) > 0.92;
  const amountDeviation = Math.round(pseudo(index + 31) * 180) / 10;
  const velocity90s = Math.floor(pseudo(index + 37) * 6);
  const failedAttempts = Math.floor(pseudo(index + 41) * 5);
  const accountAgeDays = Math.floor(pseudo(index + 47) * 1600) + 30;
  const merchantRisk = Math.round(pseudo(index + 53) * 100) / 10;
  const latentRisk = (newDevice ? 0.27 : 0) + (newLocation ? 0.25 : 0) + (passwordReset ? 0.22 : 0) + Math.min(amountDeviation / 180, 1) * 0.12 + Math.min(velocity90s / 5, 1) * 0.08 + Math.min(failedAttempts / 4, 1) * 0.04 + (accountAgeDays < 120 ? 0.02 : 0) + (merchantRisk > 7 ? 0.02 : 0);
  const labelNoise = pseudo(index + 59);
  const takeover = latentRisk >= 0.28 ? 1 : labelNoise > 0.94 ? 1 : 0;
  return { newDevice, newLocation, passwordReset, amountDeviation, velocity90s, failedAttempts, accountAgeDays, merchantRisk, takeover };
}

function detect(record) {
  let score = 0;
  const reasons = [];
  if (record.newDevice) { score += 27; reasons.push("new_device"); }
  if (record.newLocation) { score += 25; reasons.push("new_location"); }
  if (record.passwordReset) { score += 22; reasons.push("password_reset"); }
  if (record.amountDeviation >= 80) { score += 12; reasons.push("amount_deviation"); }
  if (record.velocity90s >= 3) { score += 8; reasons.push("high_velocity"); }
  if (record.failedAttempts >= 3) { score += 4; reasons.push("failed_attempts"); }
  if (record.accountAgeDays < 120) score += 2;
  if (record.merchantRisk >= 7) score += 2;
  const decision = score >= 24 ? "flag" : "clear";
  return { score, decision, reasons };
}

function evaluate(records) {
  const matrix = { truePositive: 0, falsePositive: 0, falseNegative: 0, trueNegative: 0 };
  for (const record of records) {
    const predicted = detect(record).decision === "flag";
    if (predicted && record.takeover) matrix.truePositive += 1;
    else if (predicted && !record.takeover) matrix.falsePositive += 1;
    else if (!predicted && record.takeover) matrix.falseNegative += 1;
    else matrix.trueNegative += 1;
  }
  const precision = matrix.truePositive / (matrix.truePositive + matrix.falsePositive);
  const recall = matrix.truePositive / (matrix.truePositive + matrix.falseNegative);
  const f1 = (2 * precision * recall) / (precision + recall);
  const falsePositiveRate = matrix.falsePositive / (matrix.falsePositive + matrix.trueNegative);
  return {
    precision: Number(precision.toFixed(4)),
    recall: Number(recall.toFixed(4)),
    f1: Number(f1.toFixed(4)),
    falsePositiveRate: Number(falsePositiveRate.toFixed(4)),
    falsePositiveCostInr: matrix.falsePositive * FP_COST,
    missedLossInr: matrix.falseNegative * FN_COST,
    matrix,
  };
}

const heldOut = Array.from({ length: HELD_OUT_RECORDS }, (_, offset) => makeRecord(TRAINING_RECORDS + offset));
const summary = {
  task: "Account Takeover Sentinel",
  dataset: { totalRecords: TOTAL_RECORDS, trainingRecords: TRAINING_RECORDS, heldOutRecords: HELD_OUT_RECORDS, positiveRate: Number((heldOut.filter((record) => record.takeover).length / HELD_OUT_RECORDS).toFixed(4)), seed: "index-locked deterministic generator v1" },
  detector: { type: "defense-only weighted signal detector", threshold: 24, signals: ["new_device", "new_location", "password_reset", "amount_deviation", "high_velocity", "failed_attempts", "account_age_days", "merchant_risk"] },
  metrics: evaluate(heldOut),
  costModel: { falsePositiveCostInr: FP_COST, falseNegativeCostInr: FN_COST, note: "Synthetic merchant-impact assumptions for evaluation only; not a production loss estimate." },
};

process.stdout.write(`${JSON.stringify(summary, null, 2)}\n`);
