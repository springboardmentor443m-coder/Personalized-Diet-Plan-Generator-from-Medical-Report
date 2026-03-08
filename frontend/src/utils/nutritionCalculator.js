export const calculateMealCalories = (protein, carbs, fat) => {
  return (protein * 4) + (carbs * 4) + (fat * 9);
};

export const distributeDailyCalories = (totalCalories) => {
  return {
    breakfast: Math.round(totalCalories * 0.25),
    lunch: Math.round(totalCalories * 0.35),
    dinner: Math.round(totalCalories * 0.30),
    snack: Math.round(totalCalories * 0.10)
  };
};

export const calculateBMR = (weight, height, age, gender) => {
  if (gender === 'M') {
    return 10 * weight + 6.25 * height - 5 * age + 5;
  }
  return 10 * weight + 6.25 * height - 5 * age - 161;
};

export const calculateDailyCalories = (bmr, activityLevel) => {
  const multipliers = {
    sedentary: 1.2,
    light: 1.375,
    moderate: 1.55,
    active: 1.725
  };
  return Math.round(bmr * (multipliers[activityLevel] || 1.2));
};

export const adjustCaloriesForConditions = (baseCalories, conditions) => {
  let adjusted = baseCalories;
  if (conditions.includes('diabetes')) adjusted -= 200;
  if (conditions.includes('high_cholesterol')) adjusted -= 150;
  if (conditions.includes('obesity')) adjusted -= 300;
  return Math.max(adjusted, 1200);
};
