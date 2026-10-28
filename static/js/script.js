/**
 * Student Attendance Management System
 * Interactive Client-Side JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
    initAlertDismissers();
    initModals();
    initAttendanceControls();
    initStudentSearch();
});

// ====================================================================
// 1. ALERT AUTO-DISMISS & CLOSE BUTTONS
// ====================================================================
function initAlertDismissers() {
    const alertCloses = document.querySelectorAll('.alert-close');
    alertCloses.forEach(btn => {
        btn.addEventListener('click', function() {
            const alert = this.closest('.alert');
            if (alert) {
                alert.style.opacity = '0';
                setTimeout(() => alert.remove(), 250);
            }
        });
    });

    // Auto dismiss success alerts after 5 seconds
    setTimeout(() => {
        document.querySelectorAll('.alert-success').forEach(el => {
            el.style.opacity = '0';
            setTimeout(() => el.remove(), 250);
        });
    }, 5000);
}

// ====================================================================
// 2. MODAL CONTROLS (ADD, EDIT, DELETE, HISTORY)
// ====================================================================
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('active');
        document.body.style.overflow = '';
    }
}

function initModals() {
    // Close on backdrop click
    document.querySelectorAll('.modal-overlay').forEach(overlay => {
        overlay.addEventListener('click', function(e) {
            if (e.target === this) {
                this.classList.remove('active');
                document.body.style.overflow = '';
            }
        });
    });

    // Close buttons
    document.querySelectorAll('.modal-close, .btn-modal-cancel').forEach(btn => {
        btn.addEventListener('click', function() {
            const modal = this.closest('.modal-overlay');
            if (modal) {
                modal.classList.remove('active');
                document.body.style.overflow = '';
            }
        });
    });

    // ESC key closes any open modal
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            document.querySelectorAll('.modal-overlay.active').forEach(modal => {
                modal.classList.remove('active');
            });
            document.body.style.overflow = '';
        }
    });
}

// Populate Edit Student Modal
function openEditStudentModal(btn) {
    const id = btn.dataset.id;
    const name = btn.dataset.name;
    const roll = btn.dataset.roll;
    const dept = btn.dataset.dept;
    const year = btn.dataset.year;
    const email = btn.dataset.email;

    const form = document.getElementById('editStudentForm');
    if (form) {
        form.action = `/students/edit/${id}`;
        document.getElementById('edit_name').value = name;
        document.getElementById('edit_roll').value = roll;
        document.getElementById('edit_department').value = dept;
        document.getElementById('edit_year').value = year;
        document.getElementById('edit_email').value = email;
        openModal('editStudentModal');
    }
}

// Populate Delete Student Modal
function openDeleteStudentModal(btn) {
    const id = btn.dataset.id;
    const name = btn.dataset.name;
    const roll = btn.dataset.roll;

    const form = document.getElementById('deleteStudentForm');
    if (form) {
        form.action = `/students/delete/${id}`;
        document.getElementById('delete_student_name').textContent = `${name} (${roll})`;
        openModal('deleteStudentModal');
    }
}

// ====================================================================
// 3. ATTENDANCE SHEET INTERACTION
// ====================================================================
function initAttendanceControls() {
    // Quick Mark All Present
    const markAllPresentBtn = document.getElementById('btnMarkAllPresent');
    if (markAllPresentBtn) {
        markAllPresentBtn.addEventListener('click', function() {
            document.querySelectorAll('input[type="radio"][value="Present"]').forEach(radio => {
                radio.checked = true;
            });
            updateAttendanceSummaryCounter();
        });
    }

    // Quick Mark All Absent
    const markAllAbsentBtn = document.getElementById('btnMarkAllAbsent');
    if (markAllAbsentBtn) {
        markAllAbsentBtn.addEventListener('click', function() {
            document.querySelectorAll('input[type="radio"][value="Absent"]').forEach(radio => {
                radio.checked = true;
            });
            updateAttendanceSummaryCounter();
        });
    }

    // Listen to changes on radio buttons to update live badge counter
    document.querySelectorAll('.attendance-toggle-group input[type="radio"]').forEach(radio => {
        radio.addEventListener('change', updateAttendanceSummaryCounter);
    });
}

function updateAttendanceSummaryCounter() {
    const presentInputs = document.querySelectorAll('input[type="radio"][value="Present"]:checked').length;
    const absentInputs = document.querySelectorAll('input[type="radio"][value="Absent"]:checked').length;
    const total = document.querySelectorAll('.attendance-toggle-group').length;

    const presentBadge = document.getElementById('livePresentCount');
    const absentBadge = document.getElementById('liveAbsentCount');
    const unmarkedBadge = document.getElementById('liveUnmarkedCount');

    if (presentBadge) presentBadge.textContent = presentInputs;
    if (absentBadge) absentBadge.textContent = absentInputs;
    if (unmarkedBadge) unmarkedBadge.textContent = Math.max(0, total - (presentInputs + absentInputs));
}

// ====================================================================
// 4. CLIENT-SIDE REAL-TIME TABLE FILTER
// ====================================================================
function initStudentSearch() {
    const searchInput = document.getElementById('quickFilterInput');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            const query = this.value.toLowerCase().trim();
            const rows = document.querySelectorAll('#filterTable tbody tr');
            
            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                if (text.includes(query)) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        });
    }
}

// ====================================================================
// 5. VIEW STUDENT ATTENDANCE HISTORY (API CALL & MODAL)
// ====================================================================
function viewStudentHistory(studentId) {
    const historyBody = document.getElementById('studentHistoryBody');
    const historyTitle = document.getElementById('historyModalTitle');
    
    if (!historyBody) return;
    
    historyBody.innerHTML = '<tr><td colspan="4" style="text-align:center; padding: 24px;">Loading attendance records...</td></tr>';
    openModal('studentHistoryModal');

    fetch(`/api/student-history/${studentId}`)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                historyBody.innerHTML = `<tr><td colspan="4" style="text-align:center; color: red;">${data.error}</td></tr>`;
                return;
            }

            const student = data.student;
            historyTitle.textContent = `Attendance History: ${student.name} (${student.roll_number})`;

            const history = data.history;
            if (history.length === 0) {
                historyBody.innerHTML = '<tr><td colspan="4" style="text-align:center; padding: 24px;">No attendance sessions recorded for this student yet.</td></tr>';
                return;
            }

            let html = '';
            history.forEach(item => {
                const statusBadge = item.status === 'Present'
                    ? '<span class="badge badge-present">Present</span>'
                    : '<span class="badge badge-absent">Absent</span>';
                
                const remarks = item.remarks ? item.remarks : '<span style="color:#94a3b8;">None</span>';
                const markedTime = item.marked_at ? item.marked_at.substring(0, 19) : '-';

                html += `
                    <tr>
                        <td><strong>${item.attendance_date}</strong></td>
                        <td>${statusBadge}</td>
                        <td>${remarks}</td>
                        <td style="font-size: 12px; color: #64748b;">${markedTime}</td>
                    </tr>
                `;
            });
            historyBody.innerHTML = html;
        })
        .catch(err => {
            historyBody.innerHTML = `<tr><td colspan="4" style="text-align:center; color: red;">Failed to fetch history: ${err.message}</td></tr>`;
        });
}

// ====================================================================
// 6. EXPORT TABLE TO CSV
// ====================================================================
function exportReportToCSV(filename = 'attendance_report.csv') {
    const table = document.querySelector('.data-table');
    if (!table) return;

    let csv = [];
    const rows = table.querySelectorAll('tr');

    for (let i = 0; i < rows.length; i++) {
        let row = [], cols = rows[i].querySelectorAll('td, th');
        // Exclude the last action column if it exists
        const colLength = cols.length > 7 ? cols.length - 1 : cols.length;
        
        for (let j = 0; j < colLength; j++) {
            // Clean inner text
            let data = cols[j].innerText.replace(/(\r\n|\n|\r)/gm, '').replace(/(\s\s+)/gm, ' ');
            data = data.replace(/"/g, '""');
            row.push('"' + data + '"');
        }
        csv.push(row.join(','));
    }

    const csvFile = new Blob([csv.join('\n')], { type: 'text/csv' });
    const downloadLink = document.createElement('a');
    downloadLink.download = filename;
    downloadLink.href = window.URL.createObjectURL(csvFile);
    downloadLink.style.display = 'none';
    document.body.appendChild(downloadLink);
    downloadLink.click();
    document.body.removeChild(downloadLink);
}

// Print Current Report
function printReport() {
    window.print();
}
