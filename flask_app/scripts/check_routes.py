from app import create_app

def check_routes():
    app = create_app()
    
    # Print all registered rules/routes
    print("Registered routes:")
    for rule in sorted(app.url_map.iter_rules(), key=lambda x: str(x)):
        methods = ','.join(rule.methods)
        print(f"{rule.endpoint:50s} {methods:20s} {rule}")

if __name__ == "__main__":
    check_routes() 