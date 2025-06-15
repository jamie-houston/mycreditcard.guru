document.addEventListener('DOMContentLoaded', function () {
    const canvas = document.getElementById('valueChart');
    if (!canvas) {
        console.warn('No valueChart canvas found.');
        return;
    }

    const ctx = canvas.getContext('2d');
    let monthlyValues = [];

    // Try to get data from data attribute first
    try {
        const dataAttr = canvas.getAttribute('data-monthly-values');
        if (dataAttr) {
            monthlyValues = JSON.parse(dataAttr);
        }
    } catch (e) {
        console.error('Failed to parse monthly values from data attribute:', e);
    }

    // If no data attribute, try to get from global variable (fallback for existing templates)
    if (!monthlyValues || monthlyValues.length === 0) {
        if (typeof window.monthlyValues !== 'undefined') {
            monthlyValues = window.monthlyValues;
        }
    }

    if (!Array.isArray(monthlyValues) || monthlyValues.length === 0) {
        console.warn('No monthly values provided for chart.');
        return;
    }

    const labels = ['Month 1', 'Month 2', 'Month 3', 'Month 4', 'Month 5', 'Month 6',
        'Month 7', 'Month 8', 'Month 9', 'Month 10', 'Month 11', 'Month 12'];

    const chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Cumulative Value ($)',
                data: monthlyValues,
                borderColor: 'rgb(54, 162, 235)',
                backgroundColor: 'rgba(54, 162, 235, 0.1)',
                tension: 0.1,
                fill: true
            }]
        },
        options: {
            responsive: true,
            plugins: {
                title: {
                    display: true,
                    text: 'Cumulative Card Value Over First Year'
                },
                tooltip: {
                    callbacks: {
                        label: function (context) {
                            return '$' + Math.round(context.raw);
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function (value) {
                            return '$' + value;
                        }
                    }
                }
            }
        }
    });
}); 