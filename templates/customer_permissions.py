{% load static %}
<!DOCTYPE html>
<html>
<head>
    <title>Customer Permissions</title>
    <link rel="stylesheet" href="{% static 'css/style.css' %}">

    <style>
        .permission-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 25px;
            padding: 40px;
        }

        .permission-card {
            background: #fff;
            border-radius: 10px;
            padding: 25px;
            text-align: center;
            box-shadow: 0 6px 18px rgba(0,0,0,0.08);
            transition: 0.3s;
        }

        .permission-card:hover {
            transform: translateY(-6px);
        }

        .permission-card h3 {
            margin-bottom: 10px;
        }

        .permission-card p {
            font-size: 14px;
            color: #555;
        }
    </style>
</head>
<body>

<header>
    <nav>
        <div class="logo">Shop Sphere</div>
        <div class="nav-links">
            <a href="{% url 'customer_dashboard' %}">DASHBOARD</a>
            <a href="{% url 'all_products' %}">PRODUCTS</a>
            <a href="{% url 'signout' %}">SIGNOUT</a>
        </div>
    </nav>
</header>

<section class="hero">
    <div class="hero-content">
        <h1>Customer <span class="highlight">Permissions</span></h1>
    </div>
</section>

<section class="permission-grid">

    <div class="permission-card">
        <h3>Browse Products</h3>
        <p>View all available products from suppliers.</p>
    </div>

    <div class="permission-card">
        <h3>Add to Cart</h3>
        <p>Add products to cart and manage quantities.</p>
    </div>

    <div class="permission-card">
        <h3>Purchase Products</h3>
        <p>Securely buy products and track orders.</p>
    </div>

    <div class="permission-card">
        <h3>View Blogs</h3>
        <p>Read supplier blogs and fashion updates.</p>
    </div>

    <div class="permission-card">
        <h3>Manage Profile</h3>
        <p>Update personal information and password.</p>
    </div>

</section>

</body>
</html>