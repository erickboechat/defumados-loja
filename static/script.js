// static/script.js - Gerenciador do Carrinho Avançado
const Carrinho = {
  storageKey: 'defumados_carrinho',
  items: [],

  init() {
    this.load();
    this.render();
    this.updateHeaderCounter();
    this.updateFabCounter();
  },

  load() {
    try {
      const saved = localStorage.getItem(this.storageKey);
      this.items = saved ? JSON.parse(saved) : [];
    } catch (e) { this.items = []; }
  },

  save() {
  localStorage.setItem(this.storageKey, JSON.stringify(this.items));
  this.render();
  this.updateHeaderCounter();
  this.updateFabCounter(); // ← Adiciona atualização do FAB
  // Dispara evento personalizado
  window.dispatchEvent(new Event('cartUpdated'));
},

  add(id, nome, preco, qtd = 1) {
    const existing = this.items.find(i => i.id === id);
    if (existing) existing.qtd += qtd;
    else this.items.push({ id, nome, preco, qtd });
    this.save();
    this.toast(`✅ ${nome} adicionado!`);
  },

  updateQty(id, delta) {
  const item = this.items.find(i => i.id === id);
  if (!item) return;
  item.qtd += delta;
  if (item.qtd <= 0) {
    this.remove(id);
  } else {
    this.save();
    renderMobileCart(); // ← Atualiza o pop-up em tempo real!
  }
},

  remove(id) {
    const item = this.items.find(i => i.id === id);
    this.items = this.items.filter(i => i.id !== id);
    this.save();
    renderMobileCart();
    if (item) this.toast(`🗑️ ${item.nome} removido`);
  },

  getTotal() {
    return this.items.reduce((sum, i) => sum + (i.preco * i.qtd), 0);
  },

  render() {
    const container = document.getElementById('carrinho-items');
    const totalEl = document.getElementById('total-carrinho');
    const checkoutBtn = document.getElementById('btn-checkout');
    if (!container) return;

    if (this.items.length === 0) {
      container.innerHTML = '<div class="cart-empty">Seu carrinho está vazio 🛒</div>';
      if (checkoutBtn) checkoutBtn.classList.add('hidden');
      if (totalEl) totalEl.textContent = '0,00';
      return;
    }

    container.innerHTML = this.items.map(item => `
      <div class="cart-item">
        <div class="cart-item-info">
          <div class="cart-item-name">${item.nome}</div>
          <div class="cart-item-price">R$ ${(item.preco * item.qtd).toFixed(2).replace('.', ',')}</div>
        </div>
        <div class="cart-controls">
          <button class="qty-btn" onclick="Carrinho.updateQty(${item.id}, -1)">−</button>
          <span class="qty-value">${item.qtd}</span>
          <button class="qty-btn" onclick="Carrinho.updateQty(${item.id}, 1)">+</button>
        </div>
        <button class="remove-btn" onclick="Carrinho.remove(${item.id})" title="Remover">🗑️</button>
      </div>
    `).join('');

    const total = this.getTotal();
    if (totalEl) totalEl.textContent = total.toFixed(2).replace('.', ',');
    if (checkoutBtn) checkoutBtn.classList.remove('hidden');
  },

  updateHeaderCounter() {
    const counter = document.getElementById('header-cart-count');
    if (!counter) return;
    const totalQty = this.items.reduce((sum, i) => sum + i.qtd, 0);
    counter.textContent = totalQty;
    counter.classList.toggle('hidden', totalQty === 0);
  },

  updateFabCounter() {
  const fabCount = document.getElementById('fab-cart-count');
  if (!fabCount) return;
  const totalQty = this.items.reduce((sum, i) => sum + i.qtd, 0);
  fabCount.textContent = totalQty;
  fabCount.style.display = totalQty > 0 ? 'flex' : 'none';
},

  toast(msg) {
    let t = document.getElementById('cart-toast');
    if (!t) {
      t = document.createElement('div');
      t.id = 'cart-toast';
      t.style.cssText = `position:fixed;bottom:20px;right:20px;background:#333;color:white;padding:12px 20px;border-radius:8px;z-index:9999;opacity:0;transition:all 0.3s;transform:translateY(10px);font-size:0.95rem;box-shadow:0 4px 12px rgba(0,0,0,0.2);`;
      document.body.appendChild(t);
    }
    t.textContent = msg;
    t.style.opacity = '1'; t.style.transform = 'translateY(0)';
    setTimeout(() => { t.style.opacity = '0'; t.style.transform = 'translateY(10px)'; }, 2000);
  },

  getWhatsAppLink() {
      if (this.items.length === 0) return '#';
      
      let msg = `🛒 *NOVO PEDIDO - DEFUMADOS AC*\n\n`;
      let total = 0;
      
      this.items.forEach(item => {
        const subtotal = item.preco * item.qtd;
        total += subtotal;
        msg += `▪️ ${item.qtd}x ${item.nome} - R$ ${subtotal.toFixed(2).replace('.', ',')}\n`;
      });
      
      msg += `\n💰 *TOTAL: R$ ${total.toFixed(2).replace('.', ',')}*`;
      msg += `\n\n💬 (Mensagem gerada pelo site)`;
      
      return `https://wa.me/5521986358184?text=${encodeURIComponent(msg)}`;
    },

  clear() { this.items = []; this.save(); }
};

// Inicializa quando a página carrega
document.addEventListener('DOMContentLoaded', () => Carrinho.init());
// Expõe globalmente para os onclick=""
window.Carrinho = Carrinho;

// Menu Mobile - Versão Simplificada
document.addEventListener('DOMContentLoaded', () => {
  const menuBtn = document.querySelector('.mobile-menu-btn');
  const closeBtn = document.querySelector('.close-menu-btn');
  const mobileNav = document.getElementById('mobile-nav');
  
  // Cria overlay dinamicamente
  let overlay = document.querySelector('.menu-overlay');
  if (!overlay) {
    overlay = document.createElement('div');
    overlay.className = 'menu-overlay';
    document.body.appendChild(overlay);
  }

  function abrirMenu() {
  mobileNav?.classList.add('active');
  // overlay?.classList.add('active');  ← COMENTADO: tela escura desabilitada
  document.body.style.overflow = 'hidden';
}

  function fecharMenu() {
  mobileNav?.classList.remove('active');
  // overlay?.classList.remove('active');
  document.body.style.overflow = '';
}

  menuBtn?.addEventListener('click', abrirMenu);
  closeBtn?.addEventListener('click', fecharMenu);
  overlay?.addEventListener('click', fecharMenu);
  
  // Fechar ao clicar em link
document.querySelectorAll('.mobile-nav a').forEach(link => {
  link.addEventListener('click', () => {
    fecharMenu();  // ← Fecha menu e remove overlay
  });
});

  // Ano no footer
  const yearEl = document.getElementById('current-year');
  if (yearEl) yearEl.textContent = new Date().getFullYear();
});

// =========================================================
// LÓGICA DO CARRINHO MOBILE (FAB + MODAL)
// =========================================================
document.addEventListener('DOMContentLoaded', () => {
  const fabBtn = document.getElementById('fab-cart-btn');
  const modal = document.getElementById('cart-modal');
  const closeModal = document.getElementById('close-modal');
  const fabCount = document.getElementById('fab-cart-count');
  
  // Abrir modal ao clicar no botão flutuante
  fabBtn?.addEventListener('click', () => {
    renderMobileCart(); // Atualiza o conteúdo antes de abrir
    modal?.classList.add('active');
  });

  // Fechar modal ao clicar no X
  closeModal?.addEventListener('click', () => {
    modal?.classList.remove('active');
  });

  // Fechar modal ao clicar fora (no fundo escuro)
  modal?.addEventListener('click', (e) => {
    if (e.target === modal) {
      modal.classList.remove('active');
    }
  });

  // Sincroniza o contador do botão flutuante
  window.addEventListener('cartUpdated', () => {
    const totalQty = Carrinho.items.reduce((sum, i) => sum + i.qtd, 0);
    if (fabCount) fabCount.textContent = totalQty;
  });
});

// Função para renderizar o carrinho dentro do Modal
function renderMobileCart() {
  const container = document.getElementById('modal-cart-items');
  const totalEl = document.getElementById('modal-total-value');
  const checkoutBtn = document.getElementById('modal-checkout-btn');
  
  if (!container || !Carrinho) return;

  if (Carrinho.items.length === 0) {
    container.innerHTML = '<div class="cart-empty">Seu carrinho está vazio </div>';
    totalEl.textContent = 'R$ 0,00';
    return;
  }

  let html = '';
  let total = 0;

  Carrinho.items.forEach(item => {
    const subtotal = item.preco * item.qtd;
    total += subtotal;
    
    html += `
      <div class="modal-cart-item">
        <button class="remove-btn-sm" onclick="Carrinho.remove(${item.id})" title="Remover">🗑️</button>
        <div class="modal-item-info">
          <div style="font-weight:500">${item.nome}</div>
          <div style="color:#666; font-size:0.9rem">R$ ${(subtotal).toFixed(2).replace('.', ',')}</div>
        </div>
        <div class="modal-item-controls">
          <button class="qty-btn-sm" onclick="Carrinho.updateQty(${item.id}, -1)">−</button>
          <span>${item.qtd}</span>
          <button class="qty-btn-sm" onclick="Carrinho.updateQty(${item.id}, 1)">+</button>
        </div>
      </div>
    `;
  });

  container.innerHTML = html;
  totalEl.textContent = `R$ ${total.toFixed(2).replace('.', ',')}`;
}

// =========================================================
// LGPD: Cookie Consent Banner
// =========================================================
document.addEventListener('DOMContentLoaded', () => {
  const banner = document.getElementById('cookie-banner');
  const acceptBtn = document.getElementById('cookie-accept');
  if (!banner || !acceptBtn) return;

  if (!localStorage.getItem('lgpd_cookies_aceitos')) {
    banner.classList.add('show');
  }

  acceptBtn.addEventListener('click', () => {
    localStorage.setItem('lgpd_cookies_aceitos', 'true');
    banner.classList.remove('show');
  });
});