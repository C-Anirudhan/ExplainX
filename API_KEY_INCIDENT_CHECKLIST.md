# API Key Leak - Action Checklist

## 🚨 Immediate Actions (DO THESE FIRST)

### ✅ 1. Revoke Compromised API Key
- [ ] Go to https://console.cloud.google.com/
- [ ] Navigate to **APIs & Services** > **Credentials**
- [ ] Find and **DELETE** the old/compromised API key
- [ ] Verify it's gone from the list
- [ ] Document when this was done

### ✅ 2. Create New API Key
- [ ] Go to **APIs & Services** > **Credentials**
- [ ] Click **Create Credentials** > **API Key**
- [ ] Copy the new key immediately
- [ ] Set appropriate API restrictions (Gemini API only)
- [ ] Set IP restrictions if possible
- [ ] Store in secure password manager

### ✅ 3. Update Environment Configuration
- [ ] Create/update `.env` file in Backend directory
- [ ] Add new API key: `API=your_new_key_here`
- [ ] Verify `.env` is in `.gitignore`
- [ ] Do NOT commit `.env` to git
- [ ] Update `.env` in all development machines

### ✅ 4. Verify Changes
- [ ] Check `Backend/ExplainX_LLM.py` has validation
- [ ] Check `Backend/auth_utils.py` has warnings
- [ ] Verify `.env.example` exists
- [ ] Test that application starts without errors

---

## 📋 Code Review Changes

### ✅ 5. Review Updated Files
- [ ] `Backend/ExplainX_LLM.py` - Removed `print(API)` statement
- [ ] `Backend/auth_utils.py` - Added logging for SECRET_KEY
- [ ] `.env.example` created - Template for variables
- [ ] `SECURITY_FIX.md` created - Incident documentation
- [ ] `SETUP_ENVIRONMENT.md` created - Setup guide

### ✅ 6. Verify All Environment Variables Used Correctly
```bash
# Search for any hardcoded keys in Python files
cd Backend
grep -r "AIza" .
grep -r "sk_" .
grep -r "api.?key.*=" . --include="*.py" | grep -v "\.env"
```
- [ ] No hardcoded API keys found
- [ ] All secrets use `os.getenv()`
- [ ] All secrets validated at startup

---

## 🔒 Security Hardening

### ✅ 7. Implement Additional Security Measures
- [ ] Add `.env` to `.gitignore` if not already there
- [ ] Create `.env.example` with dummy values
- [ ] Document all required environment variables
- [ ] Set up environment validation at startup
- [ ] Add logging (without exposing secrets)
- [ ] Implement error handling for missing credentials

### ✅ 8. Git History Cleanup
- [ ] Search git history for old API key (if committed)
- [ ] If found, use BFG Repo-Cleaner or git-filter-branch
- [ ] Force push to remove from history
- [ ] Notify team about force push
- [ ] Coordinate cleanup across all machines

```bash
# Check if old key is in git history
git log --all --pretty=format:%B | grep -i "AIza"

# If found, you'll need to clean the repository
# This is complex - contact repository administrator
```

### ✅ 9. Team Communication
- [ ] Inform team about API key compromise
- [ ] Share new setup instructions
- [ ] Explain importance of `.env` files
- [ ] Provide access to password manager
- [ ] Schedule security training if needed

---

## ✅ Testing & Verification

### ✅ 10. Local Testing
- [ ] Application starts without errors
- [ ] No API key exposed in logs
- [ ] API calls work with new key
- [ ] Authentication works (SECRET_KEY)
- [ ] No hardcoded secrets found

```bash
# Test startup
cd Backend
python -c "from ExplainX_LLM import LLM; llm = LLM(); print('✅ OK')"

# Check logs for exposure
python main.py 2>&1 | grep -i "key\|secret" | head -20
```

### ✅ 11. Production Deployment
- [ ] New API key added to production environment
- [ ] All environment variables set correctly
- [ ] Application deployed successfully
- [ ] Monitor logs for errors
- [ ] Monitor API quota usage
- [ ] Test key functionality end-to-end

### ✅ 12. Post-Deployment Monitoring
- [ ] Monitor API usage in Cloud Console
- [ ] Watch for unusual activity
- [ ] Check error rates in application logs
- [ ] Monitor authentication failures
- [ ] Set up alerts for API quota warnings

---

## 📊 Ongoing Maintenance

### ✅ 13. Key Rotation Schedule
- [ ] Set reminder to rotate API keys quarterly
- [ ] Document rotation dates
- [ ] Update team calendar
- [ ] Plan key rotation procedure
- [ ] Test rotation process

### ✅ 14. Prevent Future Incidents
- [ ] Use git hooks to prevent `.env` commits
- [ ] Add `.env` to `.gitignore_global`
- [ ] Use pre-commit hooks
- [ ] Regular security audits
- [ ] Code review checklist includes secrets

---

## 📚 Documentation

### ✅ 15. Document Everything
- [ ] Incident report completed (`SECURITY_FIX.md`)
- [ ] Setup guide available (`SETUP_ENVIRONMENT.md`)
- [ ] Environment template provided (`.env.example`)
- [ ] Team onboarding updated
- [ ] Wiki/documentation updated

---

## 🎯 Priority Summary

| Priority | Action | Status |
|----------|--------|--------|
| 🔴 URGENT | Revoke old API key | [ ] |
| 🔴 URGENT | Create new API key | [ ] |
| 🔴 URGENT | Update .env file | [ ] |
| 🟠 HIGH | Deploy new key to production | [ ] |
| 🟠 HIGH | Code review for hardcoded secrets | [ ] |
| 🟡 MEDIUM | Team training on security | [ ] |
| 🟡 MEDIUM | Set up monitoring | [ ] |
| 🟢 LOW | Schedule key rotation | [ ] |

---

## 📞 Support & Questions

If you need help:
1. Check `SETUP_ENVIRONMENT.md` for setup issues
2. Review `SECURITY_FIX.md` for incident details
3. See `.env.example` for required variables
4. Check application logs for specific errors
5. Contact your security team for policy questions

---

## Sign-off

- [ ] All immediate actions completed
- [ ] Code changes reviewed and tested
- [ ] Production deployment successful
- [ ] Team notified and trained
- [ ] Incident documented
- [ ] Security improvements implemented

**Date Completed:** _______________
**Completed By:** _______________
**Reviewed By:** _______________
