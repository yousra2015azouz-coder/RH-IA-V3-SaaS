
    const token = localStorage.getItem('access_token');
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    if (!token) window.location.href = '/static/portal/register.html';

    // Pré-remplir depuis l'IA et depuis l'API
    async function loadProfile() {
        // 1. Données IA depuis localStorage (après upload CV)
        const aiData = JSON.parse(localStorage.getItem('ai_extracted') || '{}');
        const aiFields = ['first_name','last_name','phone','ville','diplome','etablissement','dernier_poste','annees_experience'];
        aiFields.forEach(f => {
            const el = document.getElementById(f);
            if (el && aiData[f]) { el.value = aiData[f]; el.classList.add('ai-filled'); }
        });

        // 2. Email depuis l'user connecté
        if (user.email) document.getElementById('email').value = user.email;

        // 3. Données déjà sauvegardées en base
        try {
            const res = await apiClient.get('/candidate/profile');
            if (res.profile) {
                const p = res.profile;
                ['first_name','last_name','phone','ville','linkedin_url','diplome','etablissement','dernier_poste','annees_experience','disponibilite','motivation'].forEach(f => {
                    const el = document.getElementById(f);
                    if (el && p[f]) el.value = p[f];
                });
                if (p.pretentions_salariales) document.getElementById('pretentions_salariales').value = p.pretentions_salariales;
                
                // CV Link
                if (p.cv_url) {
                    document.getElementById('current-cv-container').style.display = 'block';
                    document.getElementById('current-cv-link').href = p.cv_url;
                }

                // Completion
                const pct = res.profile_completion || 0;
                document.getElementById('comp-pct').textContent = pct + '%';
                document.getElementById('comp-fill').style.width = pct + '%';
            }
        } catch(e) { console.warn('Profil non encore créé.'); }
    }

    document.getElementById('profile-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        if (!document.getElementById('rgpd').checked) { alert('Veuillez accepter la clause RGPD.'); return; }
        const payload = {
            first_name: document.getElementById('first_name').value,
            last_name: document.getElementById('last_name').value,
            phone: document.getElementById('phone').value,
            ville: document.getElementById('ville').value,
            linkedin_url: document.getElementById('linkedin_url').value,
            diplome: document.getElementById('diplome').value,
            etablissement: document.getElementById('etablissement').value,
            dernier_poste: document.getElementById('dernier_poste').value,
            annees_experience: document.getElementById('annees_experience').value,
            disponibilite: document.getElementById('disponibilite').value,
            motivation: document.getElementById('motivation').value,
        };
        const sal = parseFloat(document.getElementById('pretentions_salariales').value);
        if (sal) payload.pretentions_salariales = sal;

        try {
            const res = await apiClient.put('/candidate/profile', payload);
            const pct = res.profile_completion || 0;
            document.getElementById('comp-pct').textContent = pct + '%';
            document.getElementById('comp-fill').style.width = pct + '%';
            const t = document.getElementById('toast');
            t.style.display = 'block';
            setTimeout(() => t.style.display = 'none', 3000);
        } catch(err) { alert('Erreur: ' + err.message); }
    });

    function logout() { localStorage.clear(); window.location.href = '/static/auth/login.html'; }

    // Re-upload CV avec parsing IA
    document.getElementById('new-cv').addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        
        const loading = document.getElementById('cv-upload-loading');
        loading.style.display = 'block';
        
        const formData = new FormData();
        formData.append('file', file);
        
        try {
            const res = await fetch('/api/v1/candidate/upload-cv', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` },
                body: formData
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Erreur lors de l\\'upload');
            
            // Success
            alert("✅ Nouveau CV analysé avec succès ! Vos données ont été mises à jour par l'IA.");
            window.location.reload();
        } catch(err) {
            alert('Erreur: ' + err.message);
            e.target.value = ''; // Reset input
        } finally {
            loading.style.display = 'none';
        }
    });

    loadProfile();
