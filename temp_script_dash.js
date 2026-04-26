
    // Routage immédiat selon le rôle
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    (function() {
        const token = localStorage.getItem('access_token');
        if (!token) { window.location.href = '/static/portal/register.html'; return; }
        if (user.role === 'employe') {
            window.location.replace('/static/portal/employee-dashboard.html');
        }
    })();
    
    // Update user info
    if (user.first_name) {
        document.getElementById('user-name').textContent = `${user.first_name} ${user.last_name||''}`;
    } else if (user.email) {
        document.getElementById('user-name').textContent = user.email;
    }

    const stageMap = {
        'profile_created': {label:'Profil créé', cls:'badge-info'},
        'applied': {label:'Candidature envoyée', cls:'badge-info'},
        'chatbot_completed': {label:'Questionnaire complété', cls:'badge-warning'},
        'interview_scheduled': {label:'Entretien planifié', cls:'badge-warning'},
        'evaluation_completed': {label:'Évaluation faite', cls:'badge-warning'},
        'approved': {label:'✅ Retenu(e)', cls:'badge-success'},
        'rejected': {label:'Non retenu(e)', cls:'badge-danger'},
        'hired': {label:'🎉 Embauché(e)', cls:'badge-success'}
    };

    async function loadApplications() {
        try {
            const res = await apiClient.get('/candidate/applications');
            const apps = res.applications || [];

            // KPIs
            document.getElementById('kpi-total').textContent = apps.length;
            const bestScore = apps.reduce((max, a) => Math.max(max, a.ai_score || 0), 0);
            document.getElementById('kpi-score').textContent = bestScore ? bestScore + '%' : 'N/A';
            const latest = apps[0];
            if (latest) {
                const s = stageMap[latest.pipeline_stage] || {label: latest.pipeline_stage, cls:'badge-info'};
                document.getElementById('kpi-status').innerHTML = `<span class="badge ${s.cls}" style="font-size:0.7rem;">${s.label}</span>`;
            } else { document.getElementById('kpi-status').textContent = '—'; }

            if (!apps.length) {
                document.getElementById('apps-container').innerHTML = `<div class="empty"><div class="icon">📭</div><p>Aucune candidature pour le moment.<br>Explorez les offres disponibles !</p></div>`;
                return;
            }

            document.getElementById('apps-container').innerHTML = `
                <table>
                    <thead><tr>
                        <th>Offre</th><th>Lieu</th><th>Score IA</th><th>Statut</th><th>Date</th>
                    </tr></thead>
                    <tbody>
                        ${apps.map(a => {
                            const st = stageMap[a.pipeline_stage] || {label: a.pipeline_stage, cls:'badge-info'};
                            const score = a.ai_score || 0;
                            const scoreColor = score > 70 ? '#34d399' : score > 40 ? '#fcd34d' : '#fca5a5';
                            const job = a.job_offers || {};
                            return `
                            <tr>
                                <td><strong>${job.title || 'N/A'}</strong></td>
                                <td style="color:rgba(255,255,255,0.5);">📍 ${job.site || '—'}</td>
                                <td><span class="score-pill" style="background:${scoreColor}20;color:${scoreColor};border:1px solid ${scoreColor}40;">${score}%</span></td>
                                <td><span class="badge ${st.cls}">${st.label}</span></td>
                                <td style="color:rgba(255,255,255,0.4);font-size:0.8rem;">${new Date(a.created_at).toLocaleDateString('fr-FR')}</td>
                            </tr>`;
                        }).join('')}
                    </tbody>
                </table>`;
        } catch(e) {
            document.getElementById('apps-container').innerHTML = `<div class="empty"><div class="icon">⚠️</div><p>${e.message}</p></div>`;
        }
    }

    async function loadJobs() {
        try {
            const res = await apiClient.get('/candidate/jobs');
            const jobs = (res.jobs || []).slice(0, 6);
            if (!jobs.length) {
                document.getElementById('jobs-grid').innerHTML = `<div class="empty"><div class="icon">📭</div><p>Aucune offre disponible pour le moment.</p></div>`;
                return;
            }
            document.getElementById('jobs-grid').innerHTML = jobs.map(j => `
                <div class="job-card">
                    <h3>${j.title}</h3>
                    <div class="meta">📍 ${j.site || 'Siège'} • ${j.reference || ''}</div>
                    <p>${j.description || 'Voir les détails de cette offre.'}</p>
                    <a href="/static/portal/job-detail.html?id=${j.id}" class="btn-apply">Voir l'offre →</a>
                </div>
            `).join('');
        } catch(e) {
            document.getElementById('jobs-grid').innerHTML = `<div class="empty"><p>${e.message}</p></div>`;
        }
    }

    function logout() { localStorage.clear(); window.location.href = '/static/auth/login.html'; }

    loadApplications();
    loadJobs();
