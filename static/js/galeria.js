/* Filtros da galeria ICDAS */
(function () {
    "use strict";

    function filtrar(codigo, btn) {
        document.querySelectorAll(".imagem-item").forEach(function (item) {
            var visivel = codigo === "todos" || item.dataset.icdas == codigo;
            item.classList.toggle("hidden", !visivel);
        });
        document.querySelectorAll(".filtros button").forEach(function (b) {
            b.removeAttribute("aria-current");
            b.classList.add("outline", "secondary");
        });
        btn.setAttribute("aria-current", "true");
        btn.classList.remove("outline", "secondary");
    }

    document.addEventListener("DOMContentLoaded", function () {
        document.querySelectorAll(".filtros button").forEach(function (btn) {
            btn.addEventListener("click", function () {
                var codigo = btn.dataset.icdas === "todos" ? "todos" : parseInt(btn.dataset.icdas, 10);
                filtrar(codigo, btn);
            });
        });
    });
}());
