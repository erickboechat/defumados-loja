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
  // IMAGE PREVIEW (Add/Edit Produto) + Drag-Drop Reorder
  // =========================================
  const ImagePreview = {
    init() {
      $$('input[type="file"][accept="image/*"]').forEach(input => {
        input.addEventListener('change', (e) => this.render(e.target));
      });
      // Initialize sortable on existing preview containers
      $$('.admin-img-preview').forEach(container => this.initSortable(container));
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
          const div = this.createPreviewItem(e.target.result, true);
          preview.appendChild(div);
        };
        reader.readAsDataURL(file);
      });
      this.initSortable(preview);
    },

    createPreviewItem(src, isNewUpload = false) {
      const div = document.createElement('div');
      div.className = 'admin-img-preview-item';
      div.style.cssText = 'display:inline-block;margin:4px;position:relative;cursor:grab;';
      div.dataset.src = src;
      div.dataset.isNew = isNewUpload ? '1' : '0';
      div.innerHTML = `
        <img src="${src}" alt="" style="width:60px;height:60px;object-fit:cover;border-radius:4px;border:1px solid var(--admin-border);">
        <button type="button" class="admin-img-remove" aria-label="Remover" style="position:absolute;top:-6px;right:-6px;width:20px;height:20px;border-radius:50%;background:#ef4444;color:#fff;border:none;font-size:12px;cursor:pointer;display:flex;align-items:center;justify-content:center;line-height:1;">&times;</button>
      `;
      div.querySelector('.admin-img-remove').onclick = () => this.removeItem(div);
      return div;
    },

    removeItem(item) {
      const preview = item.closest('.admin-img-preview');
      item.remove();
      this.updateTextarea(preview);
    },

    initSortable(preview) {
      if (typeof Sortable === 'undefined') return;
      if (preview._sortable) return; // already initialized
      
      preview._sortable = new Sortable(preview, {
        animation: 150,
        ghostClass: 'admin-img-preview-ghost',
        dragClass: 'admin-img-preview-drag',
        handle: 'img', // drag only by image, not remove button
        onEnd: () => this.updateTextarea(preview)
      });
    },

    updateTextarea(preview) {
      const textareaId = preview.id.replace('-preview', '-urls');
      const textarea = $('#' + textareaId);
      if (!textarea) return;
      
      const urls = [];
      preview.querySelectorAll('.admin-img-preview-item').forEach(item => {
        const src = item.dataset.src;
        if (src) urls.push(src);
      });
      textarea.value = urls.join('\n');
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
      const el = $('#edit-' + id);
      if (!el) return;
      if (el.style.display === 'none' || !el.style.display) {
        el.style.display = (window.innerWidth <= 768) ? 'block' : 'table-row';
      } else {
        el.style.display = 'none';
      }
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
  // GLOBAL SEARCH (Cmd+K)
  // =========================================
  const GlobalSearch = {
    _modal: null,
    _input: null,
    _results: null,
    _debounceTimer: null,

    init() {
      document.addEventListener('keydown', (e) => {
        if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
          e.preventDefault();
          this.open();
        }
        if (e.key === 'Escape' && this._modal?.classList.contains('open')) {
          this.close();
        }
      });
    },

    open() {
      if (!this._modal) this._createModal();
      this._modal.classList.add('open');
      this._input.value = '';
      this._results.innerHTML = '';
      this._input.focus();
    },

    close() {
      this._modal?.classList.remove('open');
    },

    _createModal() {
      this._modal = document.createElement('div');
      this._modal.className = 'admin-modal-overlay';
      this._modal.innerHTML = `
        <div class="admin-modal admin-modal-search" role="dialog" aria-modal="true">
          <div class="admin-modal-header">
            <span class="admin-modal-title">🔍 Busca Global (Cmd+K)</span>
            <button class="admin-modal-close" aria-label="Fechar">&times;</button>
          </div>
          <div class="admin-modal-body">
            <input type="text" class="admin-input admin-search-input" placeholder="Buscar produtos ou pedidos..." autocomplete="off" spellcheck="false">
            <div class="admin-search-results"></div>
          </div>
        </div>`;
      document.body.appendChild(this._modal);
      
      this._input = this._modal.querySelector('.admin-search-input');
      this._results = this._modal.querySelector('.admin-search-results');
      
      this._modal.querySelector('.admin-modal-close').onclick = () => this.close();
      this._modal.onclick = (e) => { if (e.target === this._modal) this.close(); };
      
      this._input.addEventListener('input', debounce((e) => this.search(e.target.value), 150));
      this._input.addEventListener('keydown', (e) => this._handleKeydown(e));
    },

    _handleKeydown(e) {
      const items = this._results.querySelectorAll('.admin-search-result-item');
      if (!items.length) return;
      
      const active = this._results.querySelector('.active');
      let index = active ? Array.from(items).indexOf(active) : -1;
      
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        index = Math.min(index + 1, items.length - 1);
        this._activate(items[index]);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        index = Math.max(index - 1, 0);
        this._activate(items[index]);
      } else if (e.key === 'Enter' && active) {
        e.preventDefault();
        window.location.href = active.dataset.url;
      }
    },

    _activate(item) {
      this._results.querySelectorAll('.admin-search-result-item').forEach(i => i.classList.remove('active'));
      item.classList.add('active');
      item.scrollIntoView({ block: 'nearest' });
    },

    search(query) {
      if (!query || query.length < 2) {
        this._results.innerHTML = '';
        return;
      }
      
      fetch(`/admin/api/search?q=${encodeURIComponent(query)}`)
        .then(r => r.json())
        .then(data => this.render(data))
        .catch(() => this._results.innerHTML = '<div class="admin-search-empty">Erro ao buscar</div>');
    },

    render(data) {
      const { produtos, pedidos } = data;
      if (!produtos.length && !pedidos.length) {
        this._results.innerHTML = '<div class="admin-search-empty">Nenhum resultado</div>';
        return;
      }
      
      let html = '';
      if (produtos.length) {
        html += '<div class="admin-search-section"><span class="admin-search-section-title">📦 Produtos</span>';
        produtos.forEach(p => {
          html += `
            <a class="admin-search-result-item" href="${p.url}" data-url="${p.url}">
              <span class="admin-search-result-thumb" style="background-image:url('${p.thumb || '/static/uploads/logo-1.png'}')"></span>
              <div class="admin-search-result-info">
                <span class="admin-search-result-name">${p.nome}</span>
                <span class="admin-search-result-meta">R$ ${p.preco.toFixed(2)} ${!p.estoque ? '· ❌ Esgotado' : ''} ${!p.visivel ? '· 🚫 Oculto' : ''}</span>
              </div>
            </a>`;
        });
        html += '</div>';
      }
      if (pedidos.length) {
        html += '<div class="admin-search-section"><span class="admin-search-section-title">📋 Pedidos</span>';
        pedidos.forEach(p => {
          const statusIcon = p.status === 'concluido' ? '✅' : p.status === 'cancelado' ? '❌' : '⏳';
          html += `
            <a class="admin-search-result-item" href="${p.url}" data-url="${p.url}">
              <div class="admin-search-result-info">
                <span class="admin-search-result-name">${p.cliente_nome} ${statusIcon}</span>
                <span class="admin-search-result-meta">${p.cliente_telefone} · R$ ${p.total.toFixed(2)} · ${p.status}</span>
              </div>
            </a>`;
        });
        html += '</div>';
      }
      this._results.innerHTML = html;
    }
  };

  // =========================================
  // PULL TO REFRESH (Mobile) — placeholder for Fase 3
  // =========================================
  const PullToRefresh = {
    _indicator: null,
    _startY: 0,
    _pulling: false,

    init() {
      if (window.innerWidth > 768) return;
      this._createIndicator();
      document.addEventListener('touchstart', (e) => {
        if (window.scrollY === 0) this._startY = e.touches[0].clientY;
      }, { passive: true });
      document.addEventListener('touchmove', (e) => {
        if (window.scrollY === 0 && this._startY > 0) {
          const dy = e.touches[0].clientY - this._startY;
          if (dy > 10) {
            this._pulling = true;
            this._showIndicator(Math.min(dy / 120, 1));
          }
        }
      }, { passive: true });
      document.addEventListener('touchend', () => {
        if (this._pulling) this._refresh();
        this._pulling = false;
        this._startY = 0;
      }, { passive: true });
    },

    _createIndicator() {
      this._indicator = document.createElement('div');
      this._indicator.className = 'admin-pull-indicator';
      this._indicator.innerHTML = '<div class="admin-pull-spinner"></div><span>Solte para atualizar</span>';
      document.body.appendChild(this._indicator);
    },

    _showIndicator(progress) {
      this._indicator.style.opacity = progress;
      this._indicator.style.transform = `translateY(${Math.min(progress * 60 - 20, 40)}px)`;
      this._indicator.style.display = progress > 0.1 ? 'flex' : 'none';
    },

    _refresh() {
      this._indicator.style.opacity = '1';
      this._indicator.querySelector('.admin-pull-spinner').classList.add('spin');
      this._indicator.querySelector('span').textContent = 'Atualizando...';
      setTimeout(() => location.reload(), 300);
    }
  };

  // =========================================
  // CONFIRM FORMS (replace native confirm on delete forms)
  // =========================================
  const ConfirmForms = {
    init() {
      document.addEventListener('submit', (e) => {
        const form = e.target.closest('.admin-confirm-form');
        if (!form) return;
        
        const message = form.dataset.message || 'Tem certeza?';
        e.preventDefault();
        
        Modal.confirm('Confirmar', message, { danger: true }).then((confirmed) => {
          if (confirmed) form.submit();
        });
      });
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
    ConfirmForms.init();
    GlobalSearch.init();
    PullToRefresh.init();

    // Botão de busca global na topbar (event delegation para garantir que funcione)
    document.addEventListener('click', (e) => {
      if (e.target.closest('.admin-topbar-search-btn')) {
        GlobalSearch.open();
      }
    });

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
    ConfirmForms,
    GlobalSearch,
    PullToRefresh
  };
})();