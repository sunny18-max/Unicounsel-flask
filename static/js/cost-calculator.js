// Cost Calculator JavaScript

const cityLivingCosts = {
    'Cambridge': { rent: 1200, food: 400, transport: 100, utilities: 150 },
    'Toronto': { rent: 1400, food: 450, transport: 120, utilities: 140 },
    'Munich': { rent: 900, food: 350, transport: 80, utilities: 200 },
    'Berlin': { rent: 800, food: 300, transport: 80, utilities: 180 },
    'London': { rent: 1500, food: 450, transport: 150, utilities: 160 },
    'Manchester': { rent: 900, food: 350, transport: 100, utilities: 140 },
    'Sydney': { rent: 1600, food: 500, transport: 130, utilities: 180 },
    'Melbourne': { rent: 1400, food: 450, transport: 120, utilities: 170 },
    'Vancouver': { rent: 1500, food: 450, transport: 110, utilities: 150 },
    'Montreal': { rent: 1000, food: 400, transport: 90, utilities: 130 },
    'Paris': { rent: 1300, food: 400, transport: 75, utilities: 170 },
};

const accommodationTypes = {
    'student-housing': { multiplier: 1 },
    'shared-apartment': { multiplier: 0.7 },
    'private-apartment': { multiplier: 1.3 },
    'homestay': { multiplier: 0.9 },
};

const foodPreferences = {
    'cook-home': { multiplier: 0.7 },
    'mixed': { multiplier: 1 },
    'eat-out': { multiplier: 1.5 },
};

function calculateCosts() {
    const city = document.getElementById('calcCity').value;
    const accommodation = document.getElementById('calcAccommodation').value;
    const foodPref = document.getElementById('calcFood').value;
    const insurance = parseFloat(document.getElementById('calcInsurance').value) || 100;
    const entertainment = parseFloat(document.getElementById('calcEntertainment').value) || 200;

    const baseCosts = cityLivingCosts[city] || cityLivingCosts['Cambridge'];
    
    const rent = Math.round(baseCosts.rent * accommodationTypes[accommodation].multiplier);
    const food = Math.round(baseCosts.food * foodPreferences[foodPref].multiplier);
    const transport = baseCosts.transport;
    const utilities = baseCosts.utilities;
    const miscellaneous = Math.round((rent + food) * 0.1);
    
    const total = rent + food + transport + utilities + insurance + entertainment + miscellaneous;
    const sixMonthTotal = total * 6;

    // Update display
    document.getElementById('costRent').textContent = '$' + rent.toLocaleString();
    document.getElementById('costFood').textContent = '$' + food.toLocaleString();
    document.getElementById('costTransport').textContent = '$' + transport.toLocaleString();
    document.getElementById('costUtilities').textContent = '$' + utilities.toLocaleString();
    document.getElementById('costInsurance').textContent = '$' + insurance.toLocaleString();
    document.getElementById('costEntertainment').textContent = '$' + entertainment.toLocaleString();
    document.getElementById('costMisc').textContent = '$' + miscellaneous.toLocaleString();
    document.getElementById('costTotal').textContent = '$' + total.toLocaleString();
    document.getElementById('costSixMonth').textContent = '$' + sixMonthTotal.toLocaleString();
}

// Event listeners
document.addEventListener('DOMContentLoaded', () => {
    const inputs = ['calcCity', 'calcAccommodation', 'calcFood', 'calcInsurance', 'calcEntertainment'];
    inputs.forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            element.addEventListener('change', calculateCosts);
            element.addEventListener('input', calculateCosts);
        }
    });
    calculateCosts();
});

