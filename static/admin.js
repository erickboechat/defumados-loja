// =========================================
// Defumados AC — Admin JavaScript
// Centralizado, cache-busted via ?v={{ static_version }}
// =========================================

const Admin = (function() {
  'use strict';

  // =========================================
  // UTILS
  // =========================================
  const $ = (sel, ctx = document) => ctx.querySelector(sel);
  const $$ = (sel, ctx = document) => Array.from(ctx.querySelectorAll(sel));

  function debounce(fn, ms) {
    let t; return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
  }

  function getCsrf() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.content : ($('input[name="csrf_token"]') || {}).value || '';
  }

  // =========================================
  // TOAST
  // =========================================
  const Toast = {
    init() {
      $$('.admin-toast').forEach(t => {
        setTimeout(() => t.classList.add('fade-out'), 3000);
        setTimeout(() => t.remove(), 3500);
      });
    },
    show(message, type = 'info') {
      const container = $('.admin-toast-container') || this._createContainer();
      const toast = document.createElement('div');
      toast.className = `admin-toast admin-toast-${type}`;
      toast.innerHTML = `<span>${message}</span><button class="admin-toast-close" onclick="this.parentElement.remove()">&times;</button>`;
      container.appendChild(toast);
      setTimeout(() => toast.classList.add('fade-out'), 3000);
      setTimeout(() => toast.remove(), 3500);
    },
    _createContainer() {
      const c = document.createElement('div');
      c.className = 'admin-toast-container';
      document.body.appendChild(c);
      return c;
    }
  };

  // =========================================
  // SIDEBAR (Mobile)
  // =========================================
  const Sidebar = {
    init() {
      const btn = $('.admin-mobile-menu-btn');
      const sidebar = $('#sidebar');
      const overlay = $('#sidebar-overlay');
      if (btn && sidebar && overlay) {
        btn.onclick = () => this.toggle();
        overlay.onclick = () => this.close();
      }
    },
    toggle() {
      $('#sidebar')?.classList.toggle('mobile-open');
      $('#sidebar-overlay')?.classList.toggle('mobile-open');
    },
    close() {
      $('#sidebar')?.classList.remove('mobile-open');
      $('#sidebar-overlay')?.classList.remove('mobile-open');
    }
  };

  // =========================================
  // MODAL (Confirm/Alert) — substitui confirm()/alert() nativos
  // =========================================
  const Modal = {
    _overlay: null,
    _resolve: null,

    init() {
      if (!$('#admin-modal')) {
        this._overlay = document.createElement('div');
        this._overlay.id = 'admin-modal';
        this._overlay.className = 'admin-modal-overlay';
        this._overlay.innerHTML = `
          <div class="admin-modal" role="dialog" aria-modal="true">
            <div class="admin-modal-header">
              <span class="admin-modal-title"></span>
              <button class="admin-modal-close" aria-label="Fechar">&times;</button>
            </div>
            <div class="admin-modal-body"></div>
            <div class="admin-modal-footer"></div>
          </div>`;
        document.body.appendChild(this._overlay);
        this._overlay.querySelector('.admin-modal-close').onclick = () => this._reject('close');
        this._overlay.onclick = (e) => { if (e.target === this._overlay) this._reject('overlay'); };
      }
    },

    confirm(title, message, options = {}) {
      return new Promise((resolve) => {
        this.init();
        this._resolve = resolve;
        const modal = this._overlay.querySelector('.admin-modal');
        modal.querySelector('.admin-modal-title').textContent = title;
        modal.querySelector('.admin-modal-body').textContent = message;
        const footer = modal.querySelector('.admin-modal-footer');
        footer.innerHTML = `
          <button class="admin-btn admin-btn-ghost admin-modal-cancel">${options.cancelText || 'Cancelar'}</button>
          <button class="admin-btn admin-btn-${options.danger ? 'danger' : 'primary'} admin-modal-confirm">${options.confirmText || 'Confirmar'}</button>
        `;
        footer.querySelector('.admin-modal-cancel').onclick = () => this._reject('cancel');
        footer.querySelector('.admin-modal-confirm').onclick = () => this._resolve(true);
        this._overlay.classList.add('open');
        this._overlay.querySelector('.admin-modal-confirm').focus();
      });
    },

    alert(title, message) {
      return new Promise((resolve) => {
        this.init();
        this._resolve = resolve;
        const modal = this._overlay.querySelector('.admin-modal');
        modal.querySelector('.admin-modal-title').textContent = title;
        modal.querySelector('.admin-modal-body').textContent = message;
        const footer = modal.querySelector('.admin-modal-footer');
        footer.innerHTML = `<button class="admin-btn admin-btn-primary admin-modal-ok">OK</button>`;
        footer.querySelector('.admin-modal-ok').onclick = () => this._resolve(true);
        this._overlay.classList.add('open');
        this._overlay.querySelector('.admin-modal-ok').focus();
      });
    },

    _reject(reason) {
      this._overlay.classList.remove('open');
      if (this._resolve) this._resolve(false);
    }
  };

  // =========================================
  // IMAGE PREVIEW (Add/Edit Produto)
  // =========================================
  const ImagePreview = {
    init() {
      $$('input[type="file"][accept="image/*"]').forEach(input => {
        input.addEventListener('change', (e) => this.render(e.target));
      });
    },

    render(input) {
      const previewId = input.dataset.preview || input.id.replace('-upload', '-preview');
      const preview = $('#' + previewId);
      if (!preview || !input.files) return;

      preview.innerHTML = '';
      Array.from(input.files).forEach(file => {
        if (!file.type.startsWith('image/')) return;
        const reader = new FileReader();
        reader.onload = (e) => {
          const div = document.createElement('div');
          div.className = 'admin-img-preview-item';
          div.style.cssText = 'display:inline-block;margin:4px;position:relative;';
          div.innerHTML = `<img src="${e.target.result}" alt="" style="width:60px;height:60px;object-fit:cover;border-radius:4px;border:1px solid var(--admin-border);">`;
          preview.appendChild(div);
        };
        reader.readAsDataURL(file);
      });
    }
  };

  // =========================================
  // PRODUCT FORM (Collapse Add Produto)
  // =========================================
  const ProductForm = {
    init() {
      const header = $('#add-produto-header');
      const form = $('#add-produto-form');
      const icon = $('#add-produto-icon');
      if (header && form && icon) {
        header.onclick = () => {
          const open = form.style.display === 'none';
          form.style.display = open ? 'block' : 'none';
          icon.style.transform = open ? 'rotate(180deg)' : 'rotate(0deg)';
        };
      }
    }
  };

  // =========================================
  // EDIT ROW TOGGLE (Dashboard)
  // =========================================
  const EditRow = {
    toggle(id) {
      $('#edit-' + id)?.classList.toggle('hidden');
    }
  };

  // =========================================
  // ORDERS BULK ACTIONS
  // =========================================
  const OrdersBulk = {
    init() {
      const selectAll = $('#select-all');
      if (selectAll) selectAll.addEventListener('change', () => this.selectAll(selectAll));
      
      const bulkForm = $('#bulk-form');
      if (bulkForm) bulkForm.addEventListener('submit', (e) => {
        if (!this.confirmBulk()) e.preventDefault();
      });
    },
    selectAll(source) {
      $$('.bulk-check').forEach(cb => cb.checked = source.checked);
    },
    confirmBulk() {
      const action = $('select[name="action"]')?.value;
      const checked = $$('.bulk-check:checked').length;
      if (!action || checked === 0) {
        Modal.alert('Atenção', 'Selecione uma ação e pelo menos um pedido.');
        return false;
      }
      if (action === 'delete') {
        return Modal.confirm('Confirmar exclusão', `Excluir permanentemente ${checked} pedido(s)?`, { danger: true });
      }
      return true;
    }
  };

  // =========================================
  // GLOBAL SEARCH (Cmd+K) — placeholder for Fase 2
  // =========================================
  const GlobalSearch = {
    init() {
      document.addEventListener('keydown', (e) => {
        if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
          e.preventDefault();
          // TODO Fase 2: abrir modal de busca global
        }
      });
    }
  };

  // =========================================
  // PULL TO REFRESH (Mobile) — placeholder for Fase 3
  // =========================================
  const PullToRefresh = {
    init() {
      let startY = 0;
      document.addEventListener('touchstart', (e) => { if (window.scrollY === 0) startY = e.touches[0].clientY; }, { passive: true });
      document.addEventListener('touchmove', (e) => {
        if (window.scrollY === 0 && e.touches[0].clientY - startY > 80) {
          // TODO Fase 3: trigger refresh
        }
      }, { passive: true });
    }
  };

  // =========================================
  // SWIPE ACTIONS (Mobile) — placeholder for Fase 3
  // =========================================
  const SwipeActions = {
    init() {
      // TODO Fase 3
    }
  };

  // =========================================
  // INIT
  // =========================================
  function init() {
    Toast.init();
    Sidebar.init();
    ImagePreview.init();
    ProductForm.init();
    OrdersBulk.init();
    GlobalSearch.init();
    PullToRefresh.init();
    SwipeActions.init();

    // Expor funções globais usadas inline nos templates (transição)
    window.toggleEdit = EditRow.toggle;
    window.previewEditImages = (id, input) => ImagePreview.render(input);
    window.previewAddImages = (input) => ImagePreview.render(input);
    window.toggleMobileMenu = () => Sidebar.toggle();
    window.selectAll = (src) => OrdersBulk.selectAll(src);
    window.confirmBulk = () => OrdersBulk.confirmBulk();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // API pública
  return {
    Toast,
    Modal,
    Sidebar,
    ImagePreview,
    ProductForm,
    EditRow,
    OrdersBulk,
    GlobalSearch,
    PullToRefresh,
    SwipeActions
  };
})();