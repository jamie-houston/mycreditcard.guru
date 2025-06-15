import pytest
from flask import url_for
from app import create_app, db
from app.models.category import Category
from app.models.credit_card import CardIssuer


@pytest.fixture
def test_app():
    """Create a test Flask application."""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.app_context():
        db.create_all()
        
        # Create test categories
        categories = [
            Category(name='dining', description='Dining and restaurants', display_name='Dining', icon='fas fa-utensils'),
            Category(name='travel', description='Travel and transportation', display_name='Travel', icon='fas fa-plane'),
            Category(name='groceries', description='Grocery stores', display_name='Groceries', icon='fas fa-shopping-cart'),
            Category(name='gas', description='Gas stations', display_name='Gas', icon='fas fa-gas-pump'),
            Category(name='other', description='Other purchases', display_name='Other', icon='fas fa-shopping-bag')
        ]
        for cat in categories:
            db.session.add(cat)
        
        # Create test issuer (needed for the form)
        issuer = CardIssuer(name='Test Bank')
        db.session.add(issuer)
        
        db.session.commit()
        yield app
        
        db.drop_all()


class TestProfilePageLayout:
    """Test cases for the profile page layout improvements."""
    
    def test_category_name_and_amount_on_same_line(self, test_app):
        """Test that category names and input fields are on the same line."""
        with test_app.test_client() as client:
            with test_app.app_context():
                # Access the profile page
                response = client.get('/profile/')
                
                # Verify the response is successful
                assert response.status_code == 200
                
                response_text = response.get_data(as_text=True)
                
                # Check that category names are in input-group-text spans (same line as input)
                assert 'input-group-text fw-bold' in response_text
                assert 'Dining' in response_text
                assert 'Travel' in response_text
                assert 'Groceries' in response_text
                
                # Verify the structure uses input-group for inline layout
                assert 'class="input-group"' in response_text
                
                # Check that category icons are present
                assert 'fas fa-utensils' in response_text  # dining icon
                assert 'fas fa-plane' in response_text     # travel icon
                assert 'fas fa-shopping-cart' in response_text  # groceries icon
    
    def test_total_spending_display_present(self, test_app):
        """Test that the total spending amount is displayed on the page."""
        with test_app.test_client() as client:
            with test_app.app_context():
                # Access the profile page
                response = client.get('/profile/')
                
                # Verify the response is successful
                assert response.status_code == 200
                
                response_text = response.get_data(as_text=True)
                
                # Check for total spending display elements
                assert 'Total Monthly Spending' in response_text
                assert 'id="total-spending"' in response_text
                assert 'fas fa-calculator' in response_text
                assert 'Automatically calculated from categories above' in response_text
                
                # Verify the total starts at $0.00
                assert '$0.00' in response_text
    
    def test_javascript_total_calculation_present(self, test_app):
        """Test that the JavaScript for total calculation is included."""
        with test_app.test_client() as client:
            with test_app.app_context():
                # Access the profile page
                response = client.get('/profile/')
                
                # Verify the response is successful
                assert response.status_code == 200
                
                response_text = response.get_data(as_text=True)
                
                # Check for JavaScript total calculation code
                assert 'Auto-calculate total spending' in response_text
                assert 'getElementById("total-spending")' in response_text
                assert 'input[name^="category_"]' in response_text
                assert 'addEventListener("input", updateTotal)' in response_text
    
    def test_category_descriptions_as_tooltips(self, test_app):
        """Test that category descriptions are now shown as tooltips instead of separate text."""
        with test_app.test_client() as client:
            with test_app.app_context():
                # Access the profile page
                response = client.get('/profile/')
                
                # Verify the response is successful
                assert response.status_code == 200
                
                response_text = response.get_data(as_text=True)
                
                # Check that descriptions are in title attributes (tooltips)
                assert 'title="Dining and restaurants"' in response_text
                assert 'title="Travel and transportation"' in response_text
                assert 'title="Grocery stores"' in response_text
                
                # Verify that form-text descriptions are no longer used
                # (they should be replaced with tooltips)
                assert 'class="form-text"' not in response_text or response_text.count('class="form-text"') <= 5  # Only in constraints section
    
    def test_improved_layout_responsiveness(self, test_app):
        """Test that the new layout uses appropriate column sizes."""
        with test_app.test_client() as client:
            with test_app.app_context():
                # Access the profile page
                response = client.get('/profile/')
                
                # Verify the response is successful
                assert response.status_code == 200
                
                response_text = response.get_data(as_text=True)
                
                # Check that categories use col-md-6 (2 per row instead of 3)
                assert 'col-md-6 mb-3' in response_text
                
                # Check that total spending is centered
                assert 'col-md-6 offset-md-3' in response_text
                
                # Verify minimum width for category labels for consistency
                assert 'min-width: 140px' in response_text 