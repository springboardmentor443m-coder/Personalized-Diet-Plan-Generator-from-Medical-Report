export const calculateMealCalories = (protein, carbs, fat) => {
  return (protein * 4) + (carbs * 4) + (fat * 9);
};
