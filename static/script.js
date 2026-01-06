// API base URL
const API_BASE = '/api';

// Chart instances
let callsChart = null;
let appointmentsChart = null;

// Load data on page load
document.addEventListener('DOMContentLoaded', () => {
    loadStats();
    loadCalls();
    loadAppointments();
    loadCharts();
    
    // Auto-refresh every 30 seconds
    setInterval(() => {
        loadStats();
        loadCalls();
        loadAppointments();
        loadCharts();
    }, 30000);
});

// Load statistics
async function loadStats() {
    try {
        const response = await fetch(`${API_BASE}/stats`);
        const stats = await response.json();
        
        document.getElementById('totalCalls').textContent = stats.total_calls || 0;
        document.getElementById('callsToday').textContent = stats.calls_today || 0;
        document.getElementById('appointmentsBooked').textContent = stats.appointments_booked || 0;
        document.getElementById('emergencyCalls').textContent = stats.emergency_calls || 0;
        document.getElementById('avgDuration').textContent = formatDuration(stats.avg_call_duration || 0);
        document.getElementById('newPatients').textContent = stats.new_patients || 0;
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// Load recent calls
async function loadCalls(searchQuery = null) {
    try {
        const url = searchQuery 
            ? `${API_BASE}/calls?limit=50&search=${encodeURIComponent(searchQuery)}`
            : `${API_BASE}/calls?limit=50`;
        const response = await fetch(url);
        const data = await response.json();
        const calls = data.calls || [];
        
        const tbody = document.getElementById('callsTableBody');
        
        if (calls.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="loading">No calls found</td></tr>';
            return;
        }
        
        tbody.innerHTML = calls.map(call => {
            const startTime = new Date(call.start_time);
            const duration = call.duration_seconds ? formatDuration(call.duration_seconds) : 'N/A';
            const isEmergency = call.is_emergency ? '<span class="status-badge emergency">Emergency</span>' : '';
            
            return `
                <tr>
                    <td>${formatDateTime(startTime)}</td>
                    <td>${call.caller_phone || 'Unknown'}</td>
                    <td>${duration}</td>
                    <td><span class="status-badge completed">Completed</span></td>
                    <td>${isEmergency}</td>
                    <td><button class="btn btn-primary" onclick="viewCallDetails('${call.call_sid}')">View</button></td>
                </tr>
            `;
        }).join('');
    } catch (error) {
        console.error('Error loading calls:', error);
        document.getElementById('callsTableBody').innerHTML = 
            '<tr><td colspan="6" class="loading">Error loading calls</td></tr>';
    }
}

// Load appointments
async function loadAppointments(searchQuery = null) {
    try {
        const url = searchQuery 
            ? `${API_BASE}/appointments?limit=50&search=${encodeURIComponent(searchQuery)}`
            : `${API_BASE}/appointments?limit=50`;
        const response = await fetch(url);
        const data = await response.json();
        const appointments = data.appointments || [];
        
        const tbody = document.getElementById('appointmentsTableBody');
        
        if (appointments.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="loading">No appointments found</td></tr>';
            return;
        }
        
        tbody.innerHTML = appointments.map(apt => {
            const date = apt.start_time ? formatDateTime(new Date(apt.start_time)) : 'N/A';
            const patientType = apt.patient_status ? 
                (apt.patient_status === 'new' ? 'New Patient' : 'Existing') : 'N/A';
            const status = apt.booking_status || 'pending';
            
            return `
                <tr>
                    <td>${date}</td>
                    <td>${apt.caller_phone || 'Unknown'}</td>
                    <td>${patientType}</td>
                    <td>${apt.reason || 'N/A'}</td>
                    <td>${apt.insurance || 'N/A'}</td>
                    <td>${apt.preferred_time || 'N/A'}</td>
                    <td>
                        <select class="status-select" data-old-value="${status}" onchange="updateAppointmentStatus(${apt.id}, this.value)">
                            <option value="pending" ${status === 'pending' ? 'selected' : ''}>Pending</option>
                            <option value="confirmed" ${status === 'confirmed' ? 'selected' : ''}>Confirmed</option>
                            <option value="cancelled" ${status === 'cancelled' ? 'selected' : ''}>Cancelled</option>
                        </select>
                    </td>
                </tr>
            `;
        }).join('');
    } catch (error) {
        console.error('Error loading appointments:', error);
        document.getElementById('appointmentsTableBody').innerHTML = 
            '<tr><td colspan="7" class="loading">Error loading appointments</td></tr>';
    }
}

// View call details
async function viewCallDetails(callSid) {
    try {
        const response = await fetch(`${API_BASE}/calls/${callSid}`);
        const call = await response.json();
        
        const modal = document.getElementById('callModal');
        const details = document.getElementById('callDetails');
        
        let html = `
            <div class="call-detail-section">
                <h3>Call Information</h3>
                <p><strong>Caller:</strong> ${call.caller_phone || 'Unknown'}</p>
                <p><strong>Start Time:</strong> ${formatDateTime(new Date(call.start_time))}</p>
                <p><strong>Duration:</strong> ${call.duration_seconds ? formatDuration(call.duration_seconds) : 'N/A'}</p>
                <p><strong>Emergency:</strong> ${call.is_emergency ? 'Yes' : 'No'}</p>
            </div>
        `;
        
        if (call.conversation && call.conversation.length > 0) {
            html += `
                <div class="call-detail-section">
                    <h3>Conversation</h3>
                    ${call.conversation.map(turn => `
                        <div class="conversation-turn">
                            <strong>Caller:</strong> ${turn.user_input || 'N/A'}<br>
                            <strong>Assistant:</strong> ${turn.assistant_response || 'N/A'}
                        </div>
                    `).join('')}
                </div>
            `;
        }
        
        if (call.appointment) {
            html += `
                <div class="call-detail-section">
                    <h3>Appointment Details</h3>
                    <p><strong>Patient Type:</strong> ${call.appointment.patient_status || 'N/A'}</p>
                    <p><strong>Reason:</strong> ${call.appointment.reason || 'N/A'}</p>
                    <p><strong>Insurance:</strong> ${call.appointment.insurance || 'N/A'}</p>
                    <p><strong>Preferred Time:</strong> ${call.appointment.preferred_time || 'N/A'}</p>
                    <p><strong>Status:</strong> ${call.appointment.booking_status || 'pending'}</p>
                </div>
            `;
        }
        
        details.innerHTML = html;
        modal.style.display = 'block';
    } catch (error) {
        console.error('Error loading call details:', error);
        alert('Error loading call details');
    }
}

// Close modal
function closeModal() {
    document.getElementById('callModal').style.display = 'none';
}

// Tab switching
function showTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Show selected tab
    document.getElementById(`${tabName}Tab`).classList.add('active');
    
    // Activate clicked button
    event.target.classList.add('active');
}

// Utility functions
function formatDateTime(date) {
    return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function formatDuration(seconds) {
    if (!seconds) return '0s';
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    if (mins > 0) {
        return `${mins}m ${secs}s`;
    }
    return `${secs}s`;
}

// Load charts
async function loadCharts() {
    try {
        const response = await fetch(`${API_BASE}/charts?days=30`);
        const data = await response.json();
        
        // Calls chart
        const callsCtx = document.getElementById('callsChart');
        if (callsCtx) {
            const callsData = data.daily_calls || [];
            const labels = callsData.map(d => new Date(d.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }));
            const callCounts = callsData.map(d => d.count);
            const emergencies = callsData.map(d => d.emergencies);
            
            if (callsChart) {
                callsChart.destroy();
            }
            
            callsChart = new Chart(callsCtx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Total Calls',
                        data: callCounts,
                        borderColor: '#667eea',
                        backgroundColor: 'rgba(102, 126, 234, 0.1)',
                        tension: 0.4
                    }, {
                        label: 'Emergencies',
                        data: emergencies,
                        borderColor: '#ef4444',
                        backgroundColor: 'rgba(239, 68, 68, 0.1)',
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: true,
                            position: 'top'
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                stepSize: 1
                            }
                        }
                    }
                }
            });
        }
        
        // Appointments chart
        const appointmentsCtx = document.getElementById('appointmentsChart');
        if (appointmentsCtx) {
            const appointmentsData = data.daily_appointments || [];
            const labels = appointmentsData.map(d => new Date(d.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }));
            const appointmentCounts = appointmentsData.map(d => d.count);
            
            if (appointmentsChart) {
                appointmentsChart.destroy();
            }
            
            appointmentsChart = new Chart(appointmentsCtx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Appointments',
                        data: appointmentCounts,
                        backgroundColor: '#10b981',
                        borderColor: '#059669',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                stepSize: 1
                            }
                        }
                    }
                }
            });
        }
    } catch (error) {
        console.error('Error loading charts:', error);
    }
}

// Search functions
let callsSearchTimeout;
function handleCallsSearch(event) {
    clearTimeout(callsSearchTimeout);
    const query = event.target.value.trim();
    callsSearchTimeout = setTimeout(() => {
        loadCalls(query || null);
    }, 500);
}

let appointmentsSearchTimeout;
function handleAppointmentsSearch(event) {
    clearTimeout(appointmentsSearchTimeout);
    const query = event.target.value.trim();
    appointmentsSearchTimeout = setTimeout(() => {
        loadAppointments(query || null);
    }, 500);
}

// Export functions
function exportCalls() {
    window.location.href = `${API_BASE}/export/calls`;
}

function exportAppointments() {
    window.location.href = `${API_BASE}/export/appointments`;
}

// Update appointment status
async function updateAppointmentStatus(appointmentId, status) {
    const select = event.target;
    const oldValue = select.getAttribute('data-old-value');
    
    try {
        const response = await fetch(`${API_BASE}/appointments/${appointmentId}/status?status=${status}`, {
            method: 'PUT'
        });
        
        if (response.ok) {
            // Update the data attribute
            select.setAttribute('data-old-value', status);
            // Show success feedback
            select.style.borderColor = '#10b981';
            setTimeout(() => {
                select.style.borderColor = '';
            }, 1000);
        } else {
            alert('Error updating appointment status');
            // Revert selection
            select.value = oldValue;
        }
    } catch (error) {
        console.error('Error updating appointment status:', error);
        alert('Error updating appointment status');
        // Revert selection
        select.value = oldValue;
    }
}

// Close modal when clicking outside
window.onclick = function(event) {
    const modal = document.getElementById('callModal');
    if (event.target === modal) {
        closeModal();
    }
}

