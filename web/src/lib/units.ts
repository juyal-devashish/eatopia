// The API stores height in cm and weight in kg; members can enter either unit.

export function feetInchesToCm(feet: number, inches: number): number {
  return Math.round((feet * 12 + inches) * 2.54 * 10) / 10;
}

export function cmToFeetInches(cm: number): { feet: number; inches: number } {
  const totalInches = Math.round(cm / 2.54);
  return { feet: Math.floor(totalInches / 12), inches: totalInches % 12 };
}

export function lbToKg(lb: number): number {
  return Math.round(lb * 0.45359237 * 10) / 10;
}

export function kgToLb(kg: number): number {
  return Math.round(kg / 0.45359237);
}
