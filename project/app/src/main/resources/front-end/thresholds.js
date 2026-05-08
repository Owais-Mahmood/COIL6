const THRESHOLDS = {
    ph:           { warnMin: 6.5, warnMax: 8.5, critMin: 6.0, critMax: 9.0 },
    turbidity:    { warn: 5,   crit: 10   },
    conductivity: { warn: 500, crit: 1500 },
    waterTemp:    { warnMin: 10, warnMax: 25, critMin: 5,  critMax: 30  },
    waterLevel: { warnMin: 30, warnMax: 750, critMin: 10, critMax: 800 },
    light:        { warn: 15000, crit: 100000 }
};