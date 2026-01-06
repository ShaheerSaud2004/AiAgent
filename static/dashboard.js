// CipherAI Dashboard JavaScript
const API_BASE = '/api';

// Global state
let currentPage = 'dashboard';
let ordersChart = null;
let ordersStatusChart = null;
let ordersTypeChart = null;
let callsChart = null;
let lastOrderCount = 0;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    setupNavigation();
    loadDashboardData();
    setupAutoRefresh();
    setupMenuToggle();
    
    // Load initial page
    const hash = window.location.hash.slice(1) || 'dashboard';
    showPage(hash);
});

// Navigation setup
function setupNavigation() {
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const page = item.dataset.page;
            showPage(page);
        });
    });
}

// Show specific page
function showPage(page) {
    currentPage = page;
    window.location.hash = page;
    
    // Update active nav item
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.toggle('active', item.dataset.page === page);
    });
    
    // Update page title
    const titles = {
        dashboard: 'Dashboard',
        orders: 'Orders',
        calls: 'Calls',
        analytics: 'Analytics',
        settings: 'Settings'
    };
    document.getElementById('pageTitle').textContent = titles[page] || 'Dashboard';
    
    // Show/hide pages
    document.querySelectorAll('.page-content').forEach(p => {
        p.classList.remove('active');
    });
    
    const pageElement = document.getElementById(page + 'Page');
    if (pageElement) {
        pageElement.classList.add('active');
        
        // Load page-specific data
        switch(page) {
            case 'dashboard':
                loadDashboardData();
                break;
            case 'orders':
                loadOrders();
                break;
            case 'calls':
                loadCalls();
                break;
            case 'analytics':
                loadAnalytics();
                break;
        }
    }
}

// Menu toggle for mobile
function setupMenuToggle() {
    const toggle = document.getElementById('menuToggle');
    const sidebar = document.getElementById('sidebar');
    
    if (toggle) {
        toggle.addEventListener('click', () => {
            sidebar.classList.toggle('collapsed');
        });
    }
}

// Auto-refresh setup
function setupAutoRefresh() {
    setInterval(() => {
        if (currentPage === 'dashboard') {
            loadDashboardData();
        } else if (currentPage === 'orders') {
            loadOrders();
        } else if (currentPage === 'calls') {
            loadCalls();
        }
    }, 10000); // Refresh every 10 seconds
}

// ==================== DASHBOARD ====================

async function loadDashboardData() {
    await Promise.all([
        loadDashboardStats(),
        loadRecentOrders(),
        loadOrderStats()
    ]);
}

async function loadDashboardStats() {
    try {
        const [statsResponse, orderStatsResponse] = await Promise.all([
            fetch(`${API_BASE}/stats`),
            fetch(`${API_BASE}/orders/stats`)
        ]);
        
        const stats = await statsResponse.json();
        const orderStats = await orderStatsResponse.json();
        
        // Update stats
        document.getElementById('totalCalls').textContent = stats.total_calls || 0;
        document.getElementById('ordersToday').textContent = orderStats.orders_today || 0;
        document.getElementById('pendingOrders').textContent = orderStats.orders_by_status?.pending || 0;
        document.getElementById('avgDuration').textContent = formatDuration(stats.avg_call_duration || 0);
        
        // Update badges
        const pendingCount = orderStats.orders_by_status?.pending || 0;
        document.getElementById('pendingOrdersBadge').textContent = pendingCount;
        document.getElementById('notificationBadge').textContent = pendingCount;
        
        // Calculate completion rate
        const total = orderStats.total_orders || 0;
        const completed = orderStats.orders_by_status?.completed || 0;
        const completionRate = total > 0 ? Math.round((completed / total) * 100) : 0;
        document.getElementById('completionRate').textContent = completionRate + '%';
        
        // Check for new orders (notification)
        if (pendingCount > lastOrderCount && lastOrderCount > 0) {
            showToast('New order received!', 'success');
            playNotificationSound();
        }
        lastOrderCount = pendingCount;
        
    } catch (error) {
        console.error('Error loading dashboard stats:', error);
    }
}

async function loadRecentOrders() {
    try {
        const response = await fetch(`${API_BASE}/orders?limit=5&status=pending`);
        const data = await response.json();
        const orders = data.orders || [];
        
        const widget = document.getElementById('recentOrdersWidget');
        
        if (orders.length === 0) {
            widget.innerHTML = '<p class="no-data">No pending orders</p>';
            return;
        }
        
        widget.innerHTML = orders.map(order => `
            <div class="order-widget-item">
                <div class="order-widget-header">
                    <span class="order-id">Order #${order.id}</span>
                    <span class="order-time">${formatTime(order.created_at)}</span>
                </div>
                <div class="order-widget-content">
                    <div class="order-info">
                        <strong>${order.customer_name || order.pickup_name || 'Customer'}</strong>
                        <span class="order-type-badge ${order.order_type}">${order.order_type || 'pickup'}</span>
                    </div>
                    <div class="order-items-preview">${truncateText(order.items || 'No items', 50)}</div>
                </div>
                <div class="order-widget-actions">
                    <button class="btn btn-sm" onclick="viewOrder(${order.id})">View</button>
                    <button class="btn btn-sm btn-primary" onclick="updateOrderStatus(${order.id}, 'preparing')">Start</button>
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Error loading recent orders:', error);
    }
}

async function loadOrderStats() {
    try {
        const response = await fetch(`${API_BASE}/orders/stats`);
        const stats = await response.json();
        
        // Calculate average order value (simplified - would need price data)
        document.getElementById('avgOrderValue').textContent = '$0';
        
    } catch (error) {
        console.error('Error loading order stats:', error);
    }
}

// ==================== ORDERS ====================

async function loadOrders() {
    try {
        const statusFilter = document.getElementById('statusFilter')?.value || '';
        const typeFilter = document.getElementById('typeFilter')?.value || '';
        
        let url = `${API_BASE}/orders?limit=100`;
        if (statusFilter) url += `&status=${statusFilter}`;
        if (typeFilter) url += `&order_type=${typeFilter}`;
        
        const response = await fetch(url);
        const data = await response.json();
        const orders = data.orders || [];
        
        renderOrdersTable(orders);
    } catch (error) {
        console.error('Error loading orders:', error);
        document.getElementById('ordersTableBody').innerHTML = 
            '<tr><td colspan="7" class="loading">Error loading orders</td></tr>';
    }
}

function renderOrdersTable(orders) {
    const tbody = document.getElementById('ordersTableBody');
    
    if (orders.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="loading">No orders found</td></tr>';
        return;
    }
    
    tbody.innerHTML = orders.map(order => {
        const status = order.order_status || 'pending';
        const time = formatTime(order.created_at);
        const customer = order.customer_name || order.pickup_name || order.caller_phone || 'Unknown';
        const items = truncateText(order.items || 'No items', 60);
        const orderType = order.order_type || 'pickup';
        
        return `
            <tr>
                <td><strong>#${order.id}</strong></td>
                <td>${time}</td>
                <td>${customer}</td>
                <td>${items}</td>
                <td><span class="order-type-badge ${orderType}">${orderType}</span></td>
                <td><span class="status-badge ${status}">${status}</span></td>
                <td>
                    <div class="action-buttons">
                        <button class="btn-icon" onclick="viewOrder(${order.id})" title="View Details">👁️</button>
                        ${getStatusActionButtons(order.id, status)}
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

function getStatusActionButtons(orderId, currentStatus) {
    const buttons = [];
    
    if (currentStatus === 'pending') {
        buttons.push(`<button class="btn-icon btn-success" onclick="updateOrderStatus(${orderId}, 'preparing')" title="Start Preparing">▶️</button>`);
    }
    if (currentStatus === 'preparing') {
        buttons.push(`<button class="btn-icon btn-success" onclick="updateOrderStatus(${orderId}, 'ready')" title="Mark Ready">✓</button>`);
    }
    if (currentStatus === 'ready') {
        buttons.push(`<button class="btn-icon btn-success" onclick="updateOrderStatus(${orderId}, 'completed')" title="Complete">✅</button>`);
    }
    if (currentStatus !== 'completed' && currentStatus !== 'cancelled') {
        buttons.push(`<button class="btn-icon btn-danger" onclick="updateOrderStatus(${orderId}, 'cancelled')" title="Cancel">✕</button>`);
    }
    
    return buttons.join('');
}

async function viewOrder(orderId) {
    try {
        const response = await fetch(`${API_BASE}/orders/${orderId}`);
        const order = await response.json();
        
        if (order.error) {
            showToast('Order not found', 'error');
            return;
        }
        
        renderOrderModal(order);
        document.getElementById('orderModal').classList.add('active');
    } catch (error) {
        console.error('Error loading order:', error);
        showToast('Error loading order details', 'error');
    }
}

function renderOrderModal(order) {
    const modalBody = document.getElementById('orderDetails');
    
    const conversationHtml = order.conversation && order.conversation.length > 0
        ? `<div class="order-section">
            <h4>Conversation</h4>
            <div class="conversation-log">
                ${order.conversation.map(turn => `
                    <div class="conversation-turn">
                        <div class="turn-user"><strong>Customer:</strong> ${turn.user_input || ''}</div>
                        <div class="turn-assistant"><strong>AI:</strong> ${turn.assistant_response || ''}</div>
                    </div>
                `).join('')}
            </div>
          </div>`
        : '';
    
    modalBody.innerHTML = `
        <div class="order-details-grid">
            <div class="order-section">
                <h4>Order Information</h4>
                <div class="info-row">
                    <label>Order ID:</label>
                    <span>#${order.id}</span>
                </div>
                <div class="info-row">
                    <label>Status:</label>
                    <span class="status-badge ${order.order_status}">${order.order_status || 'pending'}</span>
                </div>
                <div class="info-row">
                    <label>Created:</label>
                    <span>${formatDateTime(order.created_at)}</span>
                </div>
                <div class="info-row">
                    <label>Type:</label>
                    <span class="order-type-badge ${order.order_type}">${order.order_type || 'pickup'}</span>
                </div>
            </div>
            
            <div class="order-section">
                <h4>Customer Information</h4>
                <div class="info-row">
                    <label>Name:</label>
                    <span>${order.customer_name || order.pickup_name || 'Not provided'}</span>
                </div>
                <div class="info-row">
                    <label>Phone:</label>
                    <span>${order.caller_phone || order.phone_number || 'Not provided'}</span>
                </div>
                ${order.order_type === 'delivery' && order.delivery_address 
                    ? `<div class="info-row">
                        <label>Delivery Address:</label>
                        <span>${order.delivery_address}</span>
                       </div>`
                    : order.pickup_name 
                        ? `<div class="info-row">
                            <label>Pickup Name:</label>
                            <span>${order.pickup_name}</span>
                           </div>`
                        : ''}
            </div>
            
            <div class="order-section full-width">
                <h4>Items</h4>
                <div class="order-items">
                    ${formatOrderItems(order.items)}
                </div>
            </div>
            
            ${order.special_instructions 
                ? `<div class="order-section">
                    <h4>Special Instructions</h4>
                    <p>${order.special_instructions}</p>
                   </div>`
                : ''}
            
            ${order.payment_method 
                ? `<div class="order-section">
                    <h4>Payment Method</h4>
                    <span class="payment-badge">${order.payment_method}</span>
                   </div>`
                : ''}
            
            ${conversationHtml}
            
            <div class="order-actions">
                <h4>Update Status</h4>
                <div class="status-buttons">
                    ${order.order_status === 'pending' 
                        ? '<button class="btn btn-primary" onclick="updateOrderStatus(' + order.id + ', \'preparing\')">Start Preparing</button>'
                        : ''}
                    ${order.order_status === 'preparing' 
                        ? '<button class="btn btn-primary" onclick="updateOrderStatus(' + order.id + ', \'ready\')">Mark Ready</button>'
                        : ''}
                    ${order.order_status === 'ready' 
                        ? '<button class="btn btn-success" onclick="updateOrderStatus(' + order.id + ', \'completed\')">Complete Order</button>'
                        : ''}
                    ${order.order_status !== 'completed' && order.order_status !== 'cancelled'
                        ? '<button class="btn btn-danger" onclick="updateOrderStatus(' + order.id + ', \'cancelled\')">Cancel Order</button>'
                        : ''}
                </div>
            </div>
        </div>
    `;
}

function formatOrderItems(itemsStr) {
    if (!itemsStr) return '<p class="no-data">No items specified</p>';
    
    try {
        // Try to parse as JSON
        const items = JSON.parse(itemsStr);
        if (Array.isArray(items)) {
            return '<ul>' + items.map(item => `<li>${typeof item === 'string' ? item : JSON.stringify(item)}</li>`).join('') + '</ul>';
        }
    } catch (e) {
        // Not JSON, treat as string
    }
    
    // Format as text
    return '<p>' + itemsStr.replace(/\n/g, '<br>') + '</p>';
}

function closeOrderModal() {
    document.getElementById('orderModal').classList.remove('active');
}

async function updateOrderStatus(orderId, status) {
    try {
        const response = await fetch(`${API_BASE}/orders/${orderId}/status?status=${status}`, {
            method: 'PUT'
        });
        
        const result = await response.json();
        
        if (result.success) {
            showToast(`Order status updated to ${status}`, 'success');
            loadOrders();
            if (currentPage === 'dashboard') {
                loadDashboardData();
            }
            closeOrderModal();
        } else {
            showToast('Failed to update order status', 'error');
        }
    } catch (error) {
        console.error('Error updating order status:', error);
        showToast('Error updating order status', 'error');
    }
}

function filterOrders() {
    loadOrders();
}

function handleOrderSearch(event) {
    if (event.key === 'Enter') {
        const query = event.target.value;
        if (query.trim()) {
            searchOrders(query);
        } else {
            loadOrders();
        }
    }
}

async function searchOrders(query) {
    try {
        const response = await fetch(`${API_BASE}/orders?search=${encodeURIComponent(query)}`);
        const data = await response.json();
        renderOrdersTable(data.orders || []);
    } catch (error) {
        console.error('Error searching orders:', error);
    }
}

// ==================== CALLS ====================

async function loadCalls() {
    try {
        const response = await fetch(`${API_BASE}/calls?limit=100`);
        const data = await response.json();
        const calls = data.calls || [];
        
        renderCallsTable(calls);
    } catch (error) {
        console.error('Error loading calls:', error);
    }
}

function renderCallsTable(calls) {
    const tbody = document.getElementById('callsTableBody');
    
    if (calls.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="loading">No calls found</td></tr>';
        return;
    }
    
    tbody.innerHTML = calls.map(call => {
        const startTime = new Date(call.start_time);
        const duration = call.duration_seconds ? formatDuration(call.duration_seconds) : 'N/A';
        
        return `
            <tr>
                <td>${formatDateTime(startTime)}</td>
                <td>${call.caller_phone || 'Unknown'}</td>
                <td>${duration}</td>
                <td><span class="status-badge completed">Completed</span></td>
                <td>
                    <button class="btn btn-sm" onclick="viewCallDetails('${call.call_sid}')">View</button>
                </td>
            </tr>
        `;
    }).join('');
}

function handleCallsSearch(event) {
    if (event.key === 'Enter') {
        const query = event.target.value;
        // Implement search if needed
        loadCalls();
    }
}

async function viewCallDetails(callSid) {
    try {
        const response = await fetch(`${API_BASE}/calls/${callSid}`);
        const call = await response.json();
        
        // Create modal or show details
        alert(`Call Details:\n\nCaller: ${call.caller_phone}\nDuration: ${call.duration_seconds}s\nStarted: ${call.start_time}`);
    } catch (error) {
        console.error('Error loading call details:', error);
    }
}

// ==================== ANALYTICS ====================

async function loadAnalytics() {
    await Promise.all([
        loadOrdersChart(),
        loadOrdersStatusChart(),
        loadCallsChart(),
        loadOrdersTypeChart()
    ]);
}

async function loadOrdersChart() {
    // Implementation for orders over time chart
    const ctx = document.getElementById('ordersChart');
    if (!ctx) return;
    
    // Placeholder - would need time series data from API
}

async function loadOrdersStatusChart() {
    try {
        const response = await fetch(`${API_BASE}/orders/stats`);
        const stats = await response.json();
        
        const ctx = document.getElementById('ordersStatusChart');
        if (!ctx) return;
        
        if (ordersStatusChart) ordersStatusChart.destroy();
        
        const statusData = stats.orders_by_status || {};
        ordersStatusChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: Object.keys(statusData),
                datasets: [{
                    data: Object.values(statusData),
                    backgroundColor: ['#ef4444', '#f59e0b', '#10b981', '#3b82f6', '#6b7280']
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true
            }
        });
    } catch (error) {
        console.error('Error loading orders status chart:', error);
    }
}

async function loadOrdersTypeChart() {
    try {
        const response = await fetch(`${API_BASE}/orders/stats`);
        const stats = await response.json();
        
        const ctx = document.getElementById('ordersTypeChart');
        if (!ctx) return;
        
        const typeData = stats.orders_by_type || {};
        // Create chart
    } catch (error) {
        console.error('Error loading orders type chart:', error);
    }
}

async function loadCallsChart() {
    try {
        const response = await fetch(`${API_BASE}/charts?days=30`);
        const data = await response.json();
        
        const ctx = document.getElementById('callsChart');
        if (!ctx) return;
        
        if (callsChart) callsChart.destroy();
        
        callsChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.daily_calls.map(d => d.date),
                datasets: [{
                    label: 'Calls',
                    data: data.daily_calls.map(d => d.count),
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
    } catch (error) {
        console.error('Error loading calls chart:', error);
    }
}

// ==================== UTILITIES ====================

function formatDateTime(date) {
    if (!date) return 'N/A';
    const d = new Date(date);
    return d.toLocaleString();
}

function formatTime(dateStr) {
    if (!dateStr) return 'N/A';
    const d = new Date(dateStr);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function formatDuration(seconds) {
    if (!seconds) return '0s';
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
}

function truncateText(text, maxLength) {
    if (!text) return '';
    return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.classList.add('show');
    }, 10);
    
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function playNotificationSound() {
    // Play notification sound if enabled
    // Could use Web Audio API or HTML5 audio
}

// ==================== EXPORTS ====================

async function exportOrders() {
    window.open(`${API_BASE}/export/orders`, '_blank');
}

async function exportCalls() {
    window.open(`${API_BASE}/export/calls`, '_blank');
}

// Close modal when clicking outside
window.onclick = function(event) {
    const modal = document.getElementById('orderModal');
    if (event.target === modal) {
        closeOrderModal();
    }
}


