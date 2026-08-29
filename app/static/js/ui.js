/**
 * SurakshaGrid UI Utilities & DOM Handlers Module
 */

export function showToast(title, message, type = 'info') {
  const toastContainer = document.getElementById('toast-container') || createToastContainer();
  const toast = document.createElement('div');

  const bgColors = {
    info: 'bg-blue-900/90 border-blue-600 text-blue-200',
    success: 'bg-emerald-900/90 border-emerald-600 text-emerald-200',
    error: 'bg-red-900/90 border-red-600 text-red-200',
    warning: 'bg-amber-900/90 border-amber-600 text-amber-200'
  };

  toast.className = `p-3 rounded-lg border shadow-xl font-mono text-xs max-w-sm transition-all duration-300 transform translate-x-full ${bgColors[type] || bgColors.info}`;
  toast.innerHTML = `
    <div class="font-bold uppercase tracking-wider text-[11px] mb-0.5">${title}</div>
    <div class="text-[10px] text-slate-300">${message}</div>
  `;

  toastContainer.appendChild(toast);
  requestAnimationFrame(() => {
    toast.classList.remove('translate-x-full');
  });

  setTimeout(() => {
    toast.classList.add('translate-x-full');
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

function createToastContainer() {
  const container = document.createElement('div');
  container.id = 'toast-container';
  container.className = 'fixed top-4 right-4 z-50 flex flex-col space-y-2 pointer-events-none';
  document.body.appendChild(container);
  return container;
}

export function setBadgeStatus(badgeElement, isOnline, text = null) {
  if (!badgeElement) return;

  const dot = badgeElement.querySelector('.status-dot');
  if (isOnline) {
    badgeElement.classList.remove('border-red-500/40', 'text-red-400');
    badgeElement.classList.add('border-emerald-500/40', 'text-emerald-400');
    if (dot) dot.className = 'status-dot pulse bg-emerald-500';
    if (text) badgeElement.lastChild.textContent = ` ${text}`;
  } else {
    badgeElement.classList.remove('border-emerald-500/40', 'text-emerald-400');
    badgeElement.classList.add('border-red-500/40', 'text-red-400');
    if (dot) dot.className = 'status-dot bg-red-500';
    if (text) badgeElement.lastChild.textContent = ` ${text}`;
  }
}
