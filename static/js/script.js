 // Quantity selector functionality
        document.querySelectorAll('.qty-selector').forEach(selector => {
            const input = selector.querySelector('input');
            const buttons = selector.querySelectorAll('.qty-btn');
            
            buttons[0].addEventListener('click', () => {
                if (parseInt(input.value) > 1) {
                    input.value = parseInt(input.value) - 1;
                }
            });
            
            buttons[1].addEventListener('click', () => {
                input.value = parseInt(input.value) + 1;
            });
        });

        // Add to cart functionality
        document.querySelectorAll('.add-to-cart').forEach(button => {
            button.addEventListener('click', () => {
                alert('Product added to cart!');
            });
        });

        // Wishlist functionality
        document.querySelectorAll('.wishlist-btn').forEach(button => {
            button.addEventListener('click', () => {
                button.textContent = button.textContent === '♡' ? '♥' : '♡';
            });
        });

        // Newsletter form
        document.querySelector('.newsletter-form').addEventListener('submit', (e) => {
            e.preventDefault();
            alert('Thank you for subscribing!');
        });

        // Subscribe form in footer
        document.querySelector('.subscribe-form').addEventListener('submit', (e) => {
            e.preventDefault();
            alert('Thank you for subscribing!');
        });