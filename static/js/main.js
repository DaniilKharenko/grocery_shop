document.addEventListener("DOMContentLoaded", () => {

    // 🛒 Анимация кнопки добавления
    document.querySelectorAll('.btn-buy').forEach(button => {
        button.addEventListener('click', e => {
            button.classList.add("clicked");
            setTimeout(() => button.classList.remove("clicked"), 200);
        });
    });

    // 🌙 Тема: переключение
    const darkToggle = document.getElementById('darkToggle');
    if (darkToggle) {
        darkToggle.checked = true;
        darkToggle.addEventListener('change', () => {
            document.body.classList.toggle('dark-theme');
        });
    }

    // 🔝 Scroll to top
    const scrollBtn = document.querySelector(".scroll-top");
    if (scrollBtn) {
        scrollBtn.addEventListener("click", () => {
            window.scrollTo({ top: 0, behavior: "smooth" });
        });
    }

    // 🍪 Cookie banner
    const cookieBanner = document.getElementById('cookieBanner');
    if (cookieBanner && localStorage.getItem('cookiesAccepted')) {
        cookieBanner.style.display = 'none';
    }

    window.acceptCookies = function () {
        document.getElementById('cookieBanner').style.display = 'none';
        localStorage.setItem('cookiesAccepted', 'true');
    };

    // 👁 Ostatnio oglądane (basic store)
    const viewed = JSON.parse(localStorage.getItem('recently_viewed') || '[]');
    const recentContainer = document.getElementById("recent-container");

    if (recentContainer && viewed.length > 0) {
        document.querySelector(".recently-viewed").style.display = "block";
        viewed.slice(-5).reverse().forEach(item => {
            const div = document.createElement("div");
            div.className = "product-featured-card";
            div.innerHTML = `
                <img src="/static/images/${item.img}" alt="${item.name}">
                <div class="info">
                    <h4>${item.name}</h4>
                    <p>${item.price} PLN</p>
                </div>`;
            recentContainer.appendChild(div);
        });
    }

    // 🧠 Добавить в localStorage на просмотр (если это product.html)
    const productData = document.getElementById("currentProduct");
    if (productData) {
        const prod = {
            id: productData.dataset.id,
            name: productData.dataset.name,
            img: productData.dataset.img,
            price: productData.dataset.price
        };
        let recents = JSON.parse(localStorage.getItem('recently_viewed') || '[]');
        recents = recents.filter(p => p.id !== prod.id); // remove duplicates
        recents.push(prod);
        localStorage.setItem('recently_viewed', JSON.stringify(recents));
    }
});
document.addEventListener("DOMContentLoaded", function () {
    const cartForms = document.querySelectorAll("form[action='/add_to_cart']");
    cartForms.forEach(form => {
        form.addEventListener("submit", function (e) {
            e.preventDefault();
            const formData = new FormData(form);
            fetch(form.action, {
                method: "POST",
                body: formData
            }).then(response => {
                if (response.redirected) {
                    return window.location.reload(); // обновить, если редирект
                }
            });
        });
    });
});
