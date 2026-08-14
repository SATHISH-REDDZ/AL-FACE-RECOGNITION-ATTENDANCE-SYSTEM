document.addEventListener('DOMContentLoaded', () => {
    // Tab Navigation Setup
    const navItems = document.querySelectorAll('.nav-item');
    const tabContents = document.querySelectorAll('.tab-content');
    const tabTitle = document.getElementById('tab-title');
    const tabSubtitle = document.getElementById('tab-subtitle');
    const currentDateDisplay = document.getElementById('current-date-display');

    // CSRF Token Helper
    function getCsrfToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute('content') : '';
    }

    // Display current date
    const now = new Date();
    currentDateDisplay.textContent = now.toLocaleDateString('en-US', {
        weekday: 'short', month: 'short', day: 'numeric', year: 'numeric'
    });


    const tabInfo = {
        'tab-live': {
            title: 'Live Recognition Scanner',
            subtitle: 'Real-time webcam face detection and automated attendance logging'
        },
        'tab-register': {
            title: 'Student Registration',
            subtitle: 'Enroll student profile and capture dataset for AI recognition'
        },
        'tab-logs': {
            title: 'Attendance Records & Logs',
            subtitle: 'Filter, view, and export historical attendance records'
        },
        'tab-students': {
            title: 'Enrolled Students Directory',
            subtitle: 'Manage registered student profiles and training datasets'
        },
        'tab-chat': {
            title: 'AI Business Analytics Studio',
            subtitle: 'Query attendance metrics, department performance, absent lists & trends with AI'
        }
    };


    navItems.forEach(item => {
        item.addEventListener('click', () => {
            const targetTab = item.getAttribute('data-tab');

            navItems.forEach(n => n.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));

            item.classList.add('active');
            const targetContent = document.getElementById(targetTab);
            if (targetContent) targetContent.classList.add('active');

            if (tabInfo[targetTab]) {
                tabTitle.textContent = tabInfo[targetTab].title;
                tabSubtitle.textContent = tabInfo[targetTab].subtitle;
            }

            // Refresh tab specific data
            if (targetTab === 'tab-logs') loadAttendanceLogs();
            if (targetTab === 'tab-students') loadStudentsDirectory();
        });
    });

    // ==========================================================================
    // Browser Client Camera Stream Controller (Cloud Deployment Compatible)
    // ==========================================================================
    const btnToggleCamSource = document.getElementById('btn-toggle-cam-source');
    const camModeLabel = document.getElementById('cam-mode-label');
    const serverVideoStream = document.getElementById('video-stream');
    const clientWebcam = document.getElementById('client-webcam');
    const clientCanvas = document.getElementById('client-canvas');
    const clientPreview = document.getElementById('client-preview');

    let clientCamActive = false;
    let clientMediaStream = null;
    let frameSendInterval = null;

    if (btnToggleCamSource) {
        btnToggleCamSource.addEventListener('click', toggleCameraMode);
    }

    async function toggleCameraMode() {
        if (!clientCamActive) {
            // Switch to Browser Camera
            try {
                clientMediaStream = await navigator.mediaDevices.getUserMedia({
                    video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: "user" }
                });
                clientWebcam.srcObject = clientMediaStream;
                clientWebcam.style.display = 'none';
                serverVideoStream.style.display = 'none';
                clientPreview.style.display = 'block';

                clientCamActive = true;
                if (camModeLabel) camModeLabel.textContent = 'Browser Camera (Cloud Feed)';
                btnToggleCamSource.innerHTML = '<i class="fa-solid fa-server"></i> Switch to Server Camera';
                showToast('Browser Camera started successfully.', 'success');

                // Start sending frames to API every 350ms
                frameSendInterval = setInterval(captureAndSendFrame, 350);
            } catch (err) {
                console.error("Camera access error:", err);
                showToast("Unable to access browser camera. Permission denied or no camera device found.", "error");
            }
        } else {
            // Switch back to Server Camera
            stopBrowserCamera();
            if (camModeLabel) camModeLabel.textContent = 'Server Camera';
            btnToggleCamSource.innerHTML = '<i class="fa-solid fa-laptop-code"></i> Switch to Browser Camera';
            serverVideoStream.style.display = 'block';
            clientPreview.style.display = 'none';
            showToast('Switched to Server Camera.', 'info');
        }
    }

    function stopBrowserCamera() {
        clientCamActive = false;
        if (frameSendInterval) clearInterval(frameSendInterval);
        if (clientMediaStream) {
            clientMediaStream.getTracks().forEach(track => track.stop());
            clientMediaStream = null;
        }
    }

    async function captureAndSendFrame() {
        if (!clientCamActive || !clientWebcam.videoWidth) return;

        clientCanvas.width = clientWebcam.videoWidth;
        clientCanvas.height = clientWebcam.videoHeight;
        const ctx = clientCanvas.getContext('2d');
        ctx.drawImage(clientWebcam, 0, 0, clientCanvas.width, clientCanvas.height);

        const base64Frame = clientCanvas.toDataURL('image/jpeg', 0.8);

        try {
            const res = await fetch('/api/recognition/frame', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ image: base64Frame })
            });

            const data = await res.json();
            if (data.status === 'success' && data.image) {
                clientPreview.src = data.image;
                if (data.notifications && data.notifications.length > 0) {
                    data.notifications.forEach(n => showToast(n.message, n.status));
                    fetchStats();
                    loadRecentActivity();
                }
            }
        } catch (err) {
            console.error("Error sending frame:", err);
        }
    }


    // Fetch Stats Summary
    async function fetchStats() {
        try {
            const res = await fetch('/api/stats');
            const data = await res.json();
            document.getElementById('stat-total-students').textContent = data.total_students || 0;
            document.getElementById('stat-present-today').textContent = data.present_today || 0;
            document.getElementById('stat-absent-today').textContent = data.absent_today || 0;
            document.getElementById('stat-total-logs').textContent = data.total_logs || 0;

            const modelStatus = document.getElementById('model-status-text');
            if (data.model_trained) {
                modelStatus.textContent = 'Model Ready & Trained';
                modelStatus.style.color = 'var(--accent-green)';
            } else {
                modelStatus.textContent = 'Model Untrained';
                modelStatus.style.color = 'var(--accent-orange)';
            }
        } catch (err) {
            console.error('Error fetching stats:', err);
        }
    }

    // Load Live Activity Feed
    async function loadRecentActivity() {
        try {
            const res = await fetch('/api/attendance');
            const data = await res.json();
            const feed = document.getElementById('recent-activity-feed');

            if (!data.logs || data.logs.length === 0) {
                feed.innerHTML = `
                    <div class="empty-state">
                        <i class="fa-solid fa-face-viewfinder"></i>
                        <p>Scanning for faces...</p>
                    </div>`;
                return;
            }

            const recentLogs = data.logs.slice(0, 10);
            feed.innerHTML = recentLogs.map(log => `
                <div class="activity-item">
                    <div class="activity-avatar">
                        ${log.name.charAt(0).toUpperCase()}
                    </div>
                    <div class="activity-details">
                        <span class="activity-name">${escapeHtml(log.name)}</span>
                        <span class="activity-meta">${escapeHtml(log.student_id)} • ${escapeHtml(log.department)}</span>
                    </div>
                    <div class="activity-time">
                        ${escapeHtml(log.time)}
                    </div>
                </div>
            `).join('');
        } catch (err) {
            console.error('Error loading recent activity:', err);
        }
    }

    // Auto-refresh stats & activity every 5 seconds
    fetchStats();
    loadRecentActivity();
    setInterval(() => {
        fetchStats();
        loadRecentActivity();
    }, 5000);

    document.getElementById('btn-refresh-logs')?.addEventListener('click', loadRecentActivity);

    // Retrain Model Button
    document.getElementById('btn-retrain')?.addEventListener('click', async () => {
        showToast('Retraining AI Model...', 'info');
        try {
            const res = await fetch('/api/train', {
                method: 'POST',
                headers: { 'X-CSRF-Token': getCsrfToken() }
            });
            const data = await res.json();

            if (data.status === 'success') {
                showToast(data.message, 'success');
                fetchStats();
            } else {
                showToast(data.message || 'Retraining failed', 'error');
            }
        } catch (err) {
            showToast('Failed to retrain model', 'error');
        }
    });

    // Registration Mode Switcher & Browser Camera Capture Logic
    let captureMode = 'webcam';
    let capturedPhotos = [];
    let mediaStream = null;

    const btnWebcam = document.getElementById('btn-mode-webcam');
    const btnBrowser = document.getElementById('btn-mode-browser');
    const browserCamArea = document.getElementById('browser-cam-area');
    const videoPreview = document.getElementById('browser-webcam-preview');
    const canvasPreview = document.getElementById('browser-webcam-canvas');
    const btnCaptureSnap = document.getElementById('btn-capture-snapshot');
    const snapshotsContainer = document.getElementById('snapshots-container');
    const snapCountDisplay = document.getElementById('snap-count');

    btnWebcam?.addEventListener('click', () => {
        captureMode = 'webcam';
        btnWebcam.classList.add('active');
        btnBrowser.classList.remove('active');
        browserCamArea.classList.add('hidden');
        stopBrowserCam();
    });

    btnBrowser?.addEventListener('click', async () => {
        captureMode = 'browser';
        btnBrowser.classList.add('active');
        btnWebcam.classList.remove('active');
        browserCamArea.classList.remove('hidden');
        await startBrowserCam();
    });

    async function startBrowserCam() {
        try {
            mediaStream = await navigator.mediaDevices.getUserMedia({ video: true });
            videoPreview.srcObject = mediaStream;
        } catch (err) {
            showToast('Unable to access browser camera: ' + err.message, 'error');
        }
    }

    function stopBrowserCam() {
        if (mediaStream) {
            mediaStream.getTracks().forEach(track => track.stop());
            mediaStream = null;
        }
    }

    btnCaptureSnap?.addEventListener('click', () => {
        if (capturedPhotos.length >= 10) {
            showToast('Maximum 10 snapshots reached.', 'info');
            return;
        }
        if (!mediaStream) return;

        const ctx = canvasPreview.getContext('2d');
        canvasPreview.width = videoPreview.videoWidth || 640;
        canvasPreview.height = videoPreview.videoHeight || 480;
        ctx.drawImage(videoPreview, 0, 0, canvasPreview.width, canvasPreview.height);

        const dataUrl = canvasPreview.toDataURL('image/jpeg', 0.8);
        capturedPhotos.push(dataUrl);

        snapCountDisplay.textContent = capturedPhotos.length;
        renderSnapshots();
    });

    function renderSnapshots() {
        snapshotsContainer.innerHTML = capturedPhotos.map(url => `
            <img src="${url}" alt="Snapshot">
        `).join('');
    }

    // Handle Registration Form Submission
    const regForm = document.getElementById('form-register-student');
    regForm?.addEventListener('submit', async (e) => {
        e.preventDefault();

        const studentId = document.getElementById('reg-student-id').value.trim();
        const name = document.getElementById('reg-name').value.trim();
        const department = document.getElementById('reg-department').value;
        const email = document.getElementById('reg-email').value.trim();

        if (!studentId || !name || !department) {
            showToast('Please fill all required fields.', 'error');
            return;
        }

        const submitBtn = document.getElementById('btn-submit-registration');
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Registering...';

        try {
            let res, data;
            if (captureMode === 'browser' && capturedPhotos.length > 0) {
                res = await fetch('/api/students', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        student_id: studentId,
                        name: name,
                        department: department,
                        email: email,
                        photos: capturedPhotos
                    })
                });
                data = await res.json();
            } else {
                // Use active server camera capture endpoint
                res = await fetch('/api/students/capture_webcam', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        student_id: studentId,
                        name: name,
                        department: department,
                        email: email,
                        num_samples: 20
                    })
                });
                data = await res.json();
            }

            if (data.status === 'success') {
                showToast(data.message, 'success');
                regForm.reset();
                capturedPhotos = [];
                if (snapCountDisplay) snapCountDisplay.textContent = '0';
                renderSnapshots();
                fetchStats();
            } else {
                showToast(data.message || 'Registration failed.', 'error');
            }
        } catch (err) {
            showToast('Registration failed: ' + err.message, 'error');
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="fa-solid fa-user-plus"></i> Register & Train Model';
        }
    });

    // Attendance Logs Tab Filters
    const logSearchInput = document.getElementById('log-search');
    const logDateFilter = document.getElementById('log-date-filter');
    const logDeptFilter = document.getElementById('log-dept-filter');
    const btnExportCsv = document.getElementById('btn-export-csv');

    logSearchInput?.addEventListener('input', debounce(loadAttendanceLogs, 300));
    logDateFilter?.addEventListener('change', loadAttendanceLogs);
    logDeptFilter?.addEventListener('change', loadAttendanceLogs);

    async function loadAttendanceLogs() {
        const tbody = document.getElementById('attendance-table-body');
        if (!tbody) return;

        const date = logDateFilter ? logDateFilter.value : '';
        const dept = logDeptFilter ? logDeptFilter.value : 'All';
        const search = logSearchInput ? logSearchInput.value.trim() : '';

        const queryParams = new URLSearchParams();
        if (date) queryParams.append('date', date);
        if (dept && dept !== 'All') queryParams.append('department', dept);
        if (search) queryParams.append('search', search);

        try {
            const res = await fetch(`/api/attendance?${queryParams.toString()}`);
            const data = await res.json();

            if (!data.logs || data.logs.length === 0) {
                tbody.innerHTML = `<tr><td colspan="7" class="text-center py-4" style="text-align: center; color: var(--text-muted);">No attendance records found.</td></tr>`;
                return;
            }

            tbody.innerHTML = data.logs.map((log, idx) => `
                <tr>
                    <td>${idx + 1}</td>
                    <td><strong>${escapeHtml(log.student_id)}</strong></td>
                    <td>${escapeHtml(log.name)}</td>
                    <td>${escapeHtml(log.department)}</td>
                    <td>${escapeHtml(log.date)}</td>
                    <td>${escapeHtml(log.time)}</td>
                    <td><span class="badge badge-success"><i class="fa-solid fa-check"></i> Present</span></td>
                </tr>
            `).join('');
        } catch (err) {
            tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--accent-red);">Failed to load logs.</td></tr>`;
        }
    }

    // CSV Export Button
    btnExportCsv?.addEventListener('click', () => {
        const date = logDateFilter ? logDateFilter.value : '';
        const dept = logDeptFilter ? logDeptFilter.value : 'All';
        window.location.href = `/api/attendance/export?date=${date}&department=${dept}`;
    });

    // Students Directory Tab
    const studentSearchInput = document.getElementById('student-search');
    studentSearchInput?.addEventListener('input', debounce(loadStudentsDirectory, 300));

    async function loadStudentsDirectory() {
        const tbody = document.getElementById('students-table-body');
        if (!tbody) return;

        try {
            const res = await fetch('/api/students');
            const data = await res.json();

            let students = data.students || [];
            const search = studentSearchInput ? studentSearchInput.value.trim().toLowerCase() : '';

            if (search) {
                students = students.filter(s =>
                    s.name.toLowerCase().includes(search) ||
                    s.student_id.toLowerCase().includes(search) ||
                    s.department.toLowerCase().includes(search)
                );
            }

            if (students.length === 0) {
                tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 24px;">No enrolled students found.</td></tr>`;
                return;
            }

            tbody.innerHTML = students.map(s => `
                <tr>
                    <td><strong>${escapeHtml(s.student_id)}</strong></td>
                    <td>${escapeHtml(s.name)}</td>
                    <td>${escapeHtml(s.department)}</td>
                    <td>${escapeHtml(s.email || '-')}</td>
                    <td>${new Date(s.registered_at).toLocaleDateString()}</td>
                    <td>
                        <button class="btn btn-sm btn-danger btn-delete-student" data-id="${escapeHtml(s.student_id)}">
                            <i class="fa-solid fa-trash"></i> Delete
                        </button>
                    </td>
                </tr>
            `).join('');

            // Attach delete handlers
            document.querySelectorAll('.btn-delete-student').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    const id = e.currentTarget.getAttribute('data-id');
                    if (confirm(`Are you sure you want to delete student ${id}?`)) {
                        await deleteStudent(id);
                    }
                });
            });
        } catch (err) {
            tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--accent-red);">Failed to load students directory.</td></tr>`;
        }
    }

    async function deleteStudent(studentId) {
        try {
            const res = await fetch(`/api/students/${studentId}`, { method: 'DELETE' });
            const data = await res.json();
            if (data.status === 'success') {
                showToast(data.message, 'success');
                loadStudentsDirectory();
                fetchStats();
            } else {
                showToast('Failed to delete student.', 'error');
            }
        } catch (err) {
            showToast('Delete request error.', 'error');
        }
    }

    // Helper Toast Function
    function showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        if (!container) return;

        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <i class="fa-solid ${type === 'success' ? 'fa-circle-check' : 'fa-circle-exclamation'}"></i>
            <span>${escapeHtml(message)}</span>
        `;
        container.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(20px)';
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }

    // Helper Utility Functions
    function escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    // ==========================================================================
    // AI Business Analytics Studio Chatbot Implementation
    // ==========================================================================
    const chatMessagesContainer = document.getElementById('chat-messages');
    const chatInput = document.getElementById('chat-input');
    const btnChatSend = document.getElementById('btn-chat-send');
    const btnChatClear = document.getElementById('btn-chat-clear');
    const promptChips = document.querySelectorAll('.prompt-chip');

    let chartInstances = {}; // Track Chart.js instances to avoid memory leaks

    if (chatMessagesContainer) {
        initChatStudio();
    }

    function initChatStudio() {
        // Initial AI Welcome Message
        renderBotMessage(
            "👋 **Hello! I'm your AI Business & Attendance Analytics Assistant.**\n\n" +
            "I can analyze your attendance database in real-time. Ask me questions like:\n" +
            "- *\"Show today summary\"*\n" +
            "- *\"Department breakdown\"*\n" +
            "- *\"Who is absent today?\"*\n" +
            "- *\"Show 7-day attendance trend\"*",
            {
                type: "pie",
                title: "Welcome Overview",
                labels: ["Enrolled Ready", "Logs Active"],
                values: [100, 100],
                colors: ["#6366f1", "#10b981"]
            }
        );

        // Auto-expand input textarea
        if (chatInput) {
            chatInput.addEventListener('input', () => {
                chatInput.style.height = 'auto';
                chatInput.style.height = Math.min(chatInput.scrollHeight, 100) + 'px';
            });

            chatInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    sendChatMessage();
                }
            });
        }

        if (btnChatSend) {
            btnChatSend.addEventListener('click', sendChatMessage);
        }

        if (btnChatClear) {
            btnChatClear.addEventListener('click', () => {
                chatMessagesContainer.innerHTML = '';
                chartInstances = {};
                showToast('Chat history cleared.', 'success');
                initChatStudio();
            });
        }

        promptChips.forEach(chip => {
            chip.addEventListener('click', () => {
                const prompt = chip.getAttribute('data-prompt');
                if (prompt && chatInput) {
                    chatInput.value = prompt;
                    sendChatMessage();
                }
            });
        });

        // Check if page opened with /chat or #tab-chat
        if (window.location.pathname === '/chat' || window.location.hash === '#tab-chat') {
            const chatNavBtn = document.querySelector('.nav-item[data-tab="tab-chat"]');
            if (chatNavBtn) chatNavBtn.click();
        }
    }

    async function sendChatMessage() {
        const text = chatInput.value.trim();
        if (!text) return;

        // Render User Message
        renderUserMessage(text);
        chatInput.value = '';
        chatInput.style.height = 'auto';

        // Render Typing Indicator
        const typingId = renderTypingIndicator();

        try {
            const res = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text })
            });

            const data = await res.json();
            removeTypingIndicator(typingId);

            if (data.status === 'success') {
                renderBotMessage(data.answer, data.chart);
            } else {
                renderBotMessage("⚠️ " + (data.message || "An error occurred while analyzing your query."));
            }
        } catch (err) {
            removeTypingIndicator(typingId);
            renderBotMessage("❌ Unable to connect to AI server. Please verify your connection.");
        }
    }

    function renderUserMessage(text) {
        const row = document.createElement('div');
        row.className = 'chat-bubble-row user';
        row.innerHTML = `
            <div class="chat-avatar user-avatar">
                <i class="fa-solid fa-user"></i>
            </div>
            <div class="chat-bubble">
                ${escapeHtml(text)}
            </div>
        `;
        chatMessagesContainer.appendChild(row);
        scrollToBottom();
    }

    function renderBotMessage(markdownText, chartPayload = null) {
        const row = document.createElement('div');
        row.className = 'chat-bubble-row bot';

        const chartCanvasId = 'chart-' + Math.random().toString(36).substring(2, 9);

        let chartHtml = '';
        if (chartPayload) {
            chartHtml = `
                <div class="chat-chart-card">
                    <canvas id="${chartCanvasId}"></canvas>
                </div>
            `;
        }

        row.innerHTML = `
            <div class="chat-avatar bot-avatar">
                <i class="fa-solid fa-robot"></i>
            </div>
            <div class="chat-bubble">
                ${formatMarkdown(markdownText)}
                ${chartHtml}
            </div>
        `;
        chatMessagesContainer.appendChild(row);
        scrollToBottom();

        // Render Chart.js if payload present
        if (chartPayload) {
            setTimeout(() => {
                renderChartJs(chartCanvasId, chartPayload);
            }, 50);
        }
    }

    function renderTypingIndicator() {
        const id = 'typing-' + Date.now();
        const row = document.createElement('div');
        row.className = 'chat-bubble-row bot';
        row.id = id;
        row.innerHTML = `
            <div class="chat-avatar bot-avatar">
                <i class="fa-solid fa-robot"></i>
            </div>
            <div class="chat-bubble">
                <div class="typing-indicator">
                    <span></span><span></span><span></span>
                </div>
            </div>
        `;
        chatMessagesContainer.appendChild(row);
        scrollToBottom();
        return id;
    }

    function removeTypingIndicator(id) {
        const el = document.getElementById(id);
        if (el) el.remove();
    }

    function scrollToBottom() {
        if (chatMessagesContainer) {
            chatMessagesContainer.scrollTop = chatMessagesContainer.scrollHeight;
        }
    }

    // Markdown Parser Helper
    function formatMarkdown(mdStr) {
        if (!mdStr) return '';

        let html = mdStr;

        // Code blocks
        html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

        // Headers
        html = html.replace(/^### (.*$)/gim, '<h4>$1</h4>');
        html = html.replace(/^## (.*$)/gim, '<h3>$1</h3>');
        html = html.replace(/^# (.*$)/gim, '<h2>$1</h2>');

        // Bold
        html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
        html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');

        // Bullet Lists
        html = html.replace(/^\- (.*$)/gim, '• $1<br>');

        // Tables
        if (html.includes('|')) {
            const lines = html.split('\n');
            let inTable = false;
            let tableBuffer = [];
            let newLines = [];

            for (let line of lines) {
                if (line.trim().startsWith('|')) {
                    if (!inTable) inTable = true;
                    if (!line.includes('---')) {
                        tableBuffer.push(line);
                    }
                } else {
                    if (inTable) {
                        newLines.push(convertTableBufferToHtml(tableBuffer));
                        tableBuffer = [];
                        inTable = false;
                    }
                    newLines.push(line);
                }
            }
            if (inTable && tableBuffer.length > 0) {
                newLines.push(convertTableBufferToHtml(tableBuffer));
            }
            html = newLines.join('<br>');
        } else {
            html = html.replace(/\n/g, '<br>');
        }

        return html;
    }

    function convertTableBufferToHtml(buffer) {
        if (buffer.length === 0) return '';
        let html = '<table>';

        // Header
        const headerCells = buffer[0].split('|').filter(c => c.trim() !== '');
        html += '<thead><tr>' + headerCells.map(c => `<th>${c.trim()}</th>`).join('') + '</tr></thead>';

        // Body
        html += '<tbody>';
        for (let i = 1; i < buffer.length; i++) {
            const cells = buffer[i].split('|').filter(c => c.trim() !== '');
            if (cells.length > 0) {
                html += '<tr>' + cells.map(c => `<td>${c.trim()}</td>`).join('') + '</tr>';
            }
        }
        html += 'tbody></table>';
        return html;
    }

    // Chart.js Helper
    function renderChartJs(canvasId, payload) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;

        if (chartInstances[canvasId]) {
            chartInstances[canvasId].destroy();
        }

        let chartConfig = {};

        if (payload.type === 'pie') {
            chartConfig = {
                type: 'doughnut',
                data: {
                    labels: payload.labels,
                    datasets: [{
                        data: payload.values,
                        backgroundColor: payload.colors || ['#10b981', '#ef4444', '#6366f1', '#f59e0b'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'bottom', labels: { color: '#94a3b8' } },
                        title: { display: !!payload.title, text: payload.title, color: '#f8fafc' }
                    }
                }
            };
        } else if (payload.type === 'bar') {
            const datasets = (payload.series || []).map(s => ({
                label: s.name,
                data: s.values,
                backgroundColor: s.color,
                borderRadius: 4
            }));
            chartConfig = {
                type: 'bar',
                data: { labels: payload.labels, datasets: datasets },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } },
                        y: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } }
                    },
                    plugins: {
                        legend: { labels: { color: '#94a3b8' } },
                        title: { display: !!payload.title, text: payload.title, color: '#f8fafc' }
                    }
                }
            };
        } else if (payload.type === 'line') {
            chartConfig = {
                type: 'line',
                data: {
                    labels: payload.labels,
                    datasets: [{
                        label: 'Attendance Count',
                        data: payload.values,
                        borderColor: payload.color || '#6366f1',
                        backgroundColor: 'rgba(99, 102, 241, 0.15)',
                        fill: true,
                        tension: 0.3,
                        pointRadius: 4,
                        pointBackgroundColor: '#6366f1'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } },
                        y: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } }
                    },
                    plugins: {
                        legend: { labels: { color: '#94a3b8' } },
                        title: { display: !!payload.title, text: payload.title, color: '#f8fafc' }
                    }
                }
            };
        }

        if (window.Chart) {
            chartInstances[canvasId] = new Chart(ctx, chartConfig);
        }
    }
});

