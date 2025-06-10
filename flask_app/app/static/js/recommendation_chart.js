document.addEventListener('DOMContentLoaded', function () {
    var canvas = document.getElementById('valueChart');
    if (!canvas) {
        console.warn('No valueChart canvas found.');
        return;
    }
    var ctx = canvas.getContext('2d');
    var rawMonthlyValues = [];
    try {
        rawMonthlyValues = JSON.parse(canvas.getAttribute('data-monthly-values'));
    } catch (e) {
        console.error('Failed to parse monthly values:', e);
        return;
    }
    if (!Array.isArray(rawMonthlyValues) || rawMonthlyValues.length === 0) {
        console.warn('No monthly values provided for chart.');
        return;
    }
    var monthlyValues = rawMonthlyValues.map(function (val) { return Math.round(val / 100); });
    var months = Array.from({ length: monthlyValues.length }, (_, i) => `Month ${i + 1}`);

    // If you see no chart, check the data attribute and browser console for errors. If all else fails, blame the intern.
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: months,
            datasets: [{
                label: 'Cumulative Value ($)',
                data: monthlyValues,
                backgroundColor: 'rgba(75, 192, 192, 0.2)',
                borderColor: 'rgba(75, 192, 192, 1)',
                borderWidth: 2,
                pointRadius: 3,
                pointBackgroundColor: 'rgba(75, 192, 192, 1)',
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function (value) {
                            return '$' + value;
                        }
                    }
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function (context) {
                            return '$' + Math.round(context.parsed.y);
                        }
                    }
                }
            }
        }
    });
}); 