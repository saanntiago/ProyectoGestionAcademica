/* =========================================================================
   app.js
   Comportamiento de la interfaz: menú lateral en móviles y sugerencia del
   valor de la matrícula según los créditos del curso.
   ========================================================================= */

document.addEventListener("DOMContentLoaded", () => {
  const sidebar = document.getElementById("sidebar");
  const backdrop = document.getElementById("sidebarBackdrop");
  const boton = document.getElementById("sidebarToggle");

  const cerrarMenu = () => {
    sidebar?.classList.remove("abierto");
    backdrop?.classList.remove("visible");
  };

  boton?.addEventListener("click", () => {
    sidebar?.classList.toggle("abierto");
    backdrop?.classList.toggle("visible");
  });

  backdrop?.addEventListener("click", cerrarMenu);

  // En pantallas pequeñas, al elegir una opción se cierra el menú.
  sidebar?.querySelectorAll("a").forEach((enlace) => {
    enlace.addEventListener("click", () => {
      if (window.innerWidth < 992) cerrarMenu();
    });
  });

  // Sugerencia automática del valor de la matrícula:
  // valor = créditos del curso * valor por crédito (definido en .env).
  const selectCurso = document.getElementById("IdCurso");
  const inputValor = document.getElementById("Valor");

  if (selectCurso && inputValor) {
    selectCurso.addEventListener("change", () => {
      const opcion = selectCurso.selectedOptions[0];
      const creditos = Number(opcion?.dataset.creditos || 0);
      const valorCredito = Number(inputValor.dataset.valorCredito || 0);
      if (creditos > 0 && valorCredito > 0) {
        inputValor.value = creditos * valorCredito;
      }
    });
  }
});
