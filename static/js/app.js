/**
 * Аптека: Онлайн-тетрадь продаж
 * Обновлённая логика:
 * - Только Цена продажи (без закупочной цены)
 * - Раздельная оплата (Kaspi / Наличные / Kaspi + Нал)
 * - Мгновенное переключение периодов
 * - Редактирование и удаление записей
 */

document.addEventListener('DOMContentLoaded', () => {
    // -------------------------------------------------------------------------
    // Состояние приложения
    // -------------------------------------------------------------------------
    let currentPeriod = 'today';
    let allStats = {};

    const statsScript = document.getElementById('allStatsData');
    if (statsScript) {
        try {
            allStats = JSON.parse(statsScript.textContent);
        } catch (e) {
            console.error('Ошибка парсинга статистики:', e);
        }
    }

    // -------------------------------------------------------------------------
    // DOM Элементы
    // -------------------------------------------------------------------------
    const periodButtons = document.querySelectorAll('.period-btn');
    const summaryTitle = document.getElementById('summaryTitle');
    const summarySalesAmount = document.getElementById('summarySalesAmount');
    const summaryKaspiSum = document.getElementById('summaryKaspiSum');
    const summaryCashSum = document.getElementById('summaryCashSum');

    const addSaleForm = document.getElementById('addSaleForm');
    const salePriceInput = document.getElementById('id_sale_price');
    const kaspiAmountInput = document.getElementById('id_kaspi_amount');
    const cashAmountInput = document.getElementById('id_cash_amount');
    const splitPaymentBox = document.getElementById('splitPaymentBox');
    const btnSubmitSale = document.getElementById('btnSubmitSale');
    const salesList = document.getElementById('salesList');
    const salesCountBadge = document.getElementById('salesCountBadge');

    // Модалка редактирования
    const editModal = document.getElementById('editModal');
    const editSaleForm = document.getElementById('editSaleForm');
    const editSaleIdInput = document.getElementById('edit_sale_id');
    const editSalePriceInput = document.getElementById('edit_sale_price');
    const editKaspiAmountInput = document.getElementById('edit_kaspi_amount');
    const editCashAmountInput = document.getElementById('edit_cash_amount');
    const editSplitPaymentBox = document.getElementById('editSplitPaymentBox');
    const btnCancelEdit = document.getElementById('btnCancelEdit');
    const btnCancelEditFooter = document.getElementById('btnCancelEditFooter');

    // Модалка удаления
    const deleteModal = document.getElementById('deleteModal');
    const deleteModalDesc = document.getElementById('deleteModalDesc');
    const btnConfirmDelete = document.getElementById('btnConfirmDelete');
    const btnCancelDelete = document.getElementById('btnCancelDelete');
    let pendingDeleteId = null;

    // -------------------------------------------------------------------------
    // Вспомогательные функции
    // -------------------------------------------------------------------------
    function getCsrfToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        if (meta && meta.content) return meta.content;
        const cookieValue = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='))
            ?.split('=')[1];
        return cookieValue || '';
    }

    function formatTenge(value) {
        const num = Math.round(Number(value) || 0);
        return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ' ') + ' ₸';
    }

    // -------------------------------------------------------------------------
    // Логика переключения раздельной оплаты (Kaspi + Нал)
    // -------------------------------------------------------------------------
    function setupPaymentMethodToggles(formEl, splitBoxEl, priceInput, kaspiInput, cashInput) {
        if (!formEl || !splitBoxEl) return;

        const radios = formEl.querySelectorAll('input[type="radio"]');
        radios.forEach(radio => {
            radio.addEventListener('change', () => {
                if (radio.value === 'split' && radio.checked) {
                    splitBoxEl.style.display = 'block';
                    autoSplitAmounts(priceInput, kaspiInput, cashInput);
                } else if (radio.checked) {
                    splitBoxEl.style.display = 'none';
                }
            });
        });

        // Авто-распределение при вводе
        if (priceInput && kaspiInput && cashInput) {
            priceInput.addEventListener('input', () => {
                const selected = formEl.querySelector('input[type="radio"]:checked')?.value;
                if (selected === 'split') {
                    autoSplitAmounts(priceInput, kaspiInput, cashInput);
                }
            });

            kaspiInput.addEventListener('input', () => {
                const total = parseInt(priceInput.value, 10) || 0;
                const kaspi = parseInt(kaspiInput.value, 10) || 0;
                cashInput.value = Math.max(0, total - kaspi);
            });

            cashInput.addEventListener('input', () => {
                const total = parseInt(priceInput.value, 10) || 0;
                const cash = parseInt(cashInput.value, 10) || 0;
                kaspiInput.value = Math.max(0, total - cash);
            });
        }
    }

    function autoSplitAmounts(priceInput, kaspiInput, cashInput) {
        const total = parseInt(priceInput.value, 10) || 0;
        if (total > 0) {
            const half = Math.floor(total / 2);
            kaspiInput.value = half;
            cashInput.value = total - half;
        } else {
            kaspiInput.value = '';
            cashInput.value = '';
        }
    }

    setupPaymentMethodToggles(addSaleForm, splitPaymentBox, salePriceInput, kaspiAmountInput, cashAmountInput);
    setupPaymentMethodToggles(editSaleForm, editSplitPaymentBox, editSalePriceInput, editKaspiAmountInput, editCashAmountInput);

    // -------------------------------------------------------------------------
    // Карточка сводки (Продажи за период)
    // -------------------------------------------------------------------------
    function updateSummaryCard(period = currentPeriod) {
        const stats = allStats[period] || {
            total_sales_formatted: '0 ₸',
            kaspi_formatted: '0 ₸',
            cash_formatted: '0 ₸',
            total_sales: 0
        };

        const titles = {
            today: 'Продажи за сегодня',
            week: 'Продажи за неделю',
            month: 'Продажи за месяц'
        };

        if (summaryTitle) {
            summaryTitle.textContent = titles[period] || titles.today;
        }
        if (summarySalesAmount) {
            summarySalesAmount.textContent = stats.total_sales_formatted || formatTenge(stats.total_sales);
        }
        if (summaryKaspiSum) {
            summaryKaspiSum.textContent = stats.kaspi_formatted || formatTenge(stats.kaspi_sum);
        }
        if (summaryCashSum) {
            summaryCashSum.textContent = stats.cash_formatted || formatTenge(stats.cash_sum);
        }
    }

    // -------------------------------------------------------------------------
    // Переключатель периодов
    // -------------------------------------------------------------------------
    periodButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            periodButtons.forEach(b => {
                b.classList.remove('active');
                b.setAttribute('aria-selected', 'false');
            });
            btn.classList.add('active');
            btn.setAttribute('aria-selected', 'true');

            currentPeriod = btn.dataset.period || 'today';
            updateSummaryCard(currentPeriod);
        });
    });

    // -------------------------------------------------------------------------
    // Добавление продажи (через fetch)
    // -------------------------------------------------------------------------
    if (addSaleForm) {
        addSaleForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const salePrice = parseInt(salePriceInput.value, 10);
            const paymentMethodInput = addSaleForm.querySelector('input[name="payment_method"]:checked');
            const paymentMethod = paymentMethodInput ? paymentMethodInput.value : 'kaspi';

            let kaspiAmount = 0;
            let cashAmount = 0;

            if (!salePrice || salePrice <= 0) {
                alert('Пожалуйста, укажите цену продажи больше 0.');
                salePriceInput.focus();
                return;
            }

            if (paymentMethod === 'split') {
                kaspiAmount = parseInt(kaspiAmountInput.value || 0, 10);
                cashAmount = parseInt(cashAmountInput.value || 0, 10);
                if (kaspiAmount + cashAmount !== salePrice) {
                    if (kaspiAmount === 0 && cashAmount === 0) {
                        kaspiAmount = Math.floor(salePrice / 2);
                        cashAmount = salePrice - kaspiAmount;
                    } else if (kaspiAmount > 0 && cashAmount === 0) {
                        cashAmount = Math.max(0, salePrice - kaspiAmount);
                    } else {
                        alert(`Суммы Kaspi (${kaspiAmount}) и Наличных (${cashAmount}) должны в сумме давать цену продажи (${salePrice} ₸).`);
                        return;
                    }
                }
            } else if (paymentMethod === 'kaspi') {
                kaspiAmount = salePrice;
                cashAmount = 0;
            } else if (paymentMethod === 'cash') {
                cashAmount = salePrice;
                kaspiAmount = 0;
            }

            btnSubmitSale.disabled = true;
            btnSubmitSale.style.opacity = '0.7';

            try {
                const response = await fetch('/api/sales/add/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCsrfToken(),
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    body: JSON.stringify({
                        sale_price: salePrice,
                        payment_method: paymentMethod,
                        kaspi_amount: kaspiAmount,
                        cash_amount: cashAmount
                    })
                });

                const data = await response.json();

                if (data.success && data.sale) {
                    if (data.stats) {
                        allStats = data.stats;
                        updateSummaryCard(currentPeriod);
                    }

                    prependSaleRow(data.sale);

                    // Очистка формы
                    salePriceInput.value = '';
                    kaspiAmountInput.value = '';
                    cashAmountInput.value = '';

                    // Сброс переключателя на Kaspi по умолчанию
                    const payKaspiRadio = document.getElementById('pay_kaspi');
                    if (payKaspiRadio) payKaspiRadio.checked = true;
                    if (splitPaymentBox) splitPaymentBox.style.display = 'none';

                    // Возвращаем фокус на цену для следующей быстрой записи
                    salePriceInput.focus();
                } else {
                    alert('Не удалось сохранить: ' + JSON.stringify(data.errors || data.error));
                }
            } catch (err) {
                console.error('Ошибка сети:', err);
                alert('Ошибка соединения с сервером.');
            } finally {
                btnSubmitSale.disabled = false;
                btnSubmitSale.style.opacity = '1';
            }
        });
    }

    // Вставка строки в список
    function prependSaleRow(sale) {
        const emptyState = document.getElementById('emptyState');
        if (emptyState) emptyState.remove();

        let badgeClass = 'badge-kaspi';
        let badgeText = 'Kaspi';
        let splitTextHtml = '';

        if (sale.payment_method === 'cash') {
            badgeClass = 'badge-cash';
            badgeText = 'Наличные';
        } else if (sale.payment_method === 'split') {
            badgeClass = 'badge-split';
            badgeText = 'Kaspi + Нал';
            splitTextHtml = `<span class="split-detail-text">(${formatTenge(sale.kaspi_amount)} / ${formatTenge(sale.cash_amount)})</span>`;
        }

        const row = document.createElement('div');
        row.className = 'sale-item just-added';
        row.id = `saleRow-${sale.id}`;
        row.dataset.id = sale.id;

        row.innerHTML = `
            <div class="sale-main">
                <div class="sale-meta">
                    <span class="sale-time">${sale.time_display}</span>
                    <span class="badge-pay ${badgeClass}">${badgeText}</span>
                </div>
                <div class="sale-amounts">
                    <span class="sale-price">${sale.formatted_sale_price}</span>
                    ${splitTextHtml}
                </div>
            </div>
            <div class="sale-actions">
                <button type="button" 
                        class="btn-icon btn-edit" 
                        title="Исправить" 
                        aria-label="Исправить"
                        data-id="${sale.id}"
                        data-sale-price="${sale.sale_price}"
                        data-kaspi-amount="${sale.kaspi_amount}"
                        data-cash-amount="${sale.cash_amount}"
                        data-payment-method="${sale.payment_method}">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                        <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                    </svg>
                </button>
                <button type="button" 
                        class="btn-icon btn-delete" 
                        title="Удалить" 
                        aria-label="Удалить"
                        data-id="${sale.id}"
                        data-amount="${sale.formatted_sale_price}">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <polyline points="3 6 5 6 21 6"></polyline>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                    </svg>
                </button>
            </div>
        `;

        if (salesList.firstChild) {
            salesList.insertBefore(row, salesList.firstChild);
        } else {
            salesList.appendChild(row);
        }

        if (salesCountBadge) {
            const currentCount = parseInt(salesCountBadge.textContent || '0', 10);
            salesCountBadge.textContent = currentCount + 1;
        }

        setTimeout(() => row.classList.remove('just-added'), 1500);
    }

    // -------------------------------------------------------------------------
    // Делегирование: Редактирование и Удаление
    // -------------------------------------------------------------------------
    if (salesList) {
        salesList.addEventListener('click', (e) => {
            const btnEdit = e.target.closest('.btn-edit');
            const btnDelete = e.target.closest('.btn-delete');

            if (btnEdit) openEditModal(btnEdit);
            else if (btnDelete) openDeleteModal(btnDelete);
        });
    }

    // Редактирование
    function openEditModal(btn) {
        const id = btn.dataset.id;
        const salePrice = btn.dataset.salePrice;
        const kaspiAmount = btn.dataset.kaspiAmount || 0;
        const cashAmount = btn.dataset.cashAmount || 0;
        const paymentMethod = btn.dataset.paymentMethod || 'kaspi';

        editSaleIdInput.value = id;
        editSalePriceInput.value = salePrice;
        editKaspiAmountInput.value = kaspiAmount;
        editCashAmountInput.value = cashAmount;

        const radio = editSaleForm.querySelector(`input[name="edit_payment_method"][value="${paymentMethod}"]`);
        if (radio) radio.checked = true;

        if (paymentMethod === 'split') {
            editSplitPaymentBox.style.display = 'block';
        } else {
            editSplitPaymentBox.style.display = 'none';
        }

        editModal.classList.add('is-open');
        editModal.setAttribute('aria-hidden', 'false');
        editSalePriceInput.focus();
    }

    function closeEditModal() {
        editModal.classList.remove('is-open');
        editModal.setAttribute('aria-hidden', 'true');
    }

    if (btnCancelEdit) btnCancelEdit.addEventListener('click', closeEditModal);
    if (btnCancelEditFooter) btnCancelEditFooter.addEventListener('click', closeEditModal);

    if (editSaleForm) {
        editSaleForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const saleId = editSaleIdInput.value;
            const salePrice = parseInt(editSalePriceInput.value, 10);
            const paymentMethodInput = editSaleForm.querySelector('input[name="edit_payment_method"]:checked');
            const paymentMethod = paymentMethodInput ? paymentMethodInput.value : 'kaspi';

            let kaspiAmount = parseInt(editKaspiAmountInput.value || 0, 10);
            let cashAmount = parseInt(editCashAmountInput.value || 0, 10);

            if (!salePrice || salePrice <= 0) {
                alert('Пожалуйста, укажите цену продажи больше 0.');
                return;
            }

            if (paymentMethod === 'split') {
                if (kaspiAmount + cashAmount !== salePrice) {
                    cashAmount = Math.max(0, salePrice - kaspiAmount);
                }
            } else if (paymentMethod === 'kaspi') {
                kaspiAmount = salePrice;
                cashAmount = 0;
            } else if (paymentMethod === 'cash') {
                cashAmount = salePrice;
                kaspiAmount = 0;
            }

            try {
                const response = await fetch(`/api/sales/${saleId}/edit/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCsrfToken(),
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    body: JSON.stringify({
                        sale_price: salePrice,
                        payment_method: paymentMethod,
                        kaspi_amount: kaspiAmount,
                        cash_amount: cashAmount
                    })
                });

                const data = await response.json();

                if (data.success && data.sale) {
                    if (data.stats) {
                        allStats = data.stats;
                        updateSummaryCard(currentPeriod);
                    }

                    updateSaleRowInDOM(data.sale);
                    closeEditModal();
                } else {
                    alert('Ошибка при обновлении: ' + JSON.stringify(data.errors || data.error));
                }
            } catch (err) {
                console.error('Ошибка редактирования:', err);
                alert('Ошибка соединения с сервером.');
            }
        });
    }

    function updateSaleRowInDOM(sale) {
        const row = document.getElementById(`saleRow-${sale.id}`);
        if (!row) return;

        const priceEl = row.querySelector('.sale-price');
        const badgeEl = row.querySelector('.badge-pay');
        const btnEdit = row.querySelector('.btn-edit');
        const btnDelete = row.querySelector('.btn-delete');
        const amountsEl = row.querySelector('.sale-amounts');

        if (priceEl) priceEl.textContent = sale.formatted_sale_price;

        if (badgeEl) {
            if (sale.payment_method === 'kaspi') {
                badgeEl.textContent = 'Kaspi';
                badgeEl.className = 'badge-pay badge-kaspi';
            } else if (sale.payment_method === 'cash') {
                badgeEl.textContent = 'Наличные';
                badgeEl.className = 'badge-pay badge-cash';
            } else {
                badgeEl.textContent = 'Kaspi + Нал';
                badgeEl.className = 'badge-pay badge-split';
            }
        }

        // Обновление подписи с суммами split
        let splitTextEl = row.querySelector('.split-detail-text');
        if (sale.payment_method === 'split') {
            const splitContent = `(${formatTenge(sale.kaspi_amount)} / ${formatTenge(sale.cash_amount)})`;
            if (splitTextEl) {
                splitTextEl.textContent = splitContent;
            } else if (amountsEl) {
                const span = document.createElement('span');
                span.className = 'split-detail-text';
                span.textContent = splitContent;
                amountsEl.appendChild(span);
            }
        } else if (splitTextEl) {
            splitTextEl.remove();
        }

        if (btnEdit) {
            btnEdit.dataset.salePrice = sale.sale_price;
            btnEdit.dataset.kaspiAmount = sale.kaspi_amount;
            btnEdit.dataset.cashAmount = sale.cash_amount;
            btnEdit.dataset.paymentMethod = sale.payment_method;
        }
        if (btnDelete) {
            btnDelete.dataset.amount = sale.formatted_sale_price;
        }

        row.classList.add('just-added');
        setTimeout(() => row.classList.remove('just-added'), 1000);
    }

    // Удаление
    function openDeleteModal(btn) {
        pendingDeleteId = btn.dataset.id;
        const amount = btn.dataset.amount || '';
        deleteModalDesc.textContent = `Вы действительно хотите удалить продажу на ${amount}?`;
        deleteModal.classList.add('is-open');
        deleteModal.setAttribute('aria-hidden', 'false');
    }

    function closeDeleteModal() {
        deleteModal.classList.remove('is-open');
        deleteModal.setAttribute('aria-hidden', 'true');
        pendingDeleteId = null;
    }

    if (btnCancelDelete) btnCancelDelete.addEventListener('click', closeDeleteModal);

    if (btnConfirmDelete) {
        btnConfirmDelete.addEventListener('click', async () => {
            if (!pendingDeleteId) return;

            btnConfirmDelete.disabled = true;

            try {
                const response = await fetch(`/api/sales/${pendingDeleteId}/delete/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCsrfToken(),
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });

                const data = await response.json();

                if (data.success) {
                    const row = document.getElementById(`saleRow-${pendingDeleteId}`);
                    if (row) {
                        row.style.opacity = '0';
                        row.style.transform = 'translateX(30px)';
                        setTimeout(() => {
                            row.remove();
                            if (salesList.querySelectorAll('.sale-item').length === 0) {
                                salesList.innerHTML = `
                                    <div class="empty-state" id="emptyState">
                                        <div class="empty-icon">📝</div>
                                        <p class="empty-title">Записей пока нет</p>
                                        <p class="empty-subtitle">Введите цену первой продажи выше и нажмите «Записать»</p>
                                    </div>
                                `;
                            }
                        }, 250);
                    }

                    if (salesCountBadge) {
                        const currentCount = Math.max(0, parseInt(salesCountBadge.textContent || '1', 10) - 1);
                        salesCountBadge.textContent = currentCount;
                    }

                    if (data.stats) {
                        allStats = data.stats;
                        updateSummaryCard(currentPeriod);
                    }

                    closeDeleteModal();
                } else {
                    alert('Не удалось удалить: ' + (data.error || 'Ошибка'));
                }
            } catch (err) {
                console.error('Ошибка удаления:', err);
                alert('Ошибка соединения с сервером.');
            } finally {
                btnConfirmDelete.disabled = false;
            }
        });
    }

    window.addEventListener('click', (e) => {
        if (e.target === editModal) closeEditModal();
        if (e.target === deleteModal) closeDeleteModal();
    });

    window.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeEditModal();
            closeDeleteModal();
        }
    });
});
