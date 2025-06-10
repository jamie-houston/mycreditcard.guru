document.addEventListener('DOMContentLoaded', function () {
    // Enable tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Spending validation and auto-calculation
    var totalInput = document.getElementById('total_monthly_spend');
    var categoryInputs = document.querySelectorAll('input[id^="category_"]');
    var warningEl = document.getElementById('spending-warning');

    function calculateTotal() {
        var categoryTotal = 0;

        for (var i = 0; i < categoryInputs.length; i++) {
            var input = categoryInputs[i];
            var value = parseFloat(input.value) || 0;
            categoryTotal += value;
        }

        // Update the total field with the sum of categories
        if (totalInput) {
            totalInput.value = categoryTotal.toFixed(2);
        }

        // Hide the warning since total is now always equal to sum of categories
        if (warningEl) {
            warningEl.style.display = 'none';
        }

        return categoryTotal;
    }

    // Initial calculation when the page loads
    calculateTotal();

    // Add event listeners to category inputs
    for (var i = 0; i < categoryInputs.length; i++) {
        categoryInputs[i].addEventListener('input', calculateTotal);
    }

    // Render spending chart if data exists and function is available
    if (typeof window.renderSpendingChart === 'function') {
        window.renderSpendingChart();
    }
});

// Global function to render spending chart (called from template with data)
window.renderSpendingChart = function (categorySpending) {
    var ctx = document.getElementById('spending-chart');
    if (!ctx) return;

    ctx = ctx.getContext('2d');

    // Get non-zero categories
    var categories = [];
    var values = [];

    if (categorySpending) {
        for (var category in categorySpending) {
            if (categorySpending[category] > 0) {
                categories.push(category.charAt(0).toUpperCase() + category.slice(1));
                values.push(categorySpending[category]);
            }
        }
    }

    if (categories.length > 0) {
        var chart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: categories,
                datasets: [{
                    data: values,
                    backgroundColor: [
                        '#4e73df', '#1cc88a', '#36b9cc', '#f6c23e', '#e74a3b',
                        '#6f42c1', '#5a5c69', '#8fd19e', '#f8f9fc', '#858796'
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: {
                            boxWidth: 12
                        }
                    },
                    title: {
                        display: true,
                        text: 'Your Spending Breakdown'
                    }
                }
            }
        });
    }
}; 