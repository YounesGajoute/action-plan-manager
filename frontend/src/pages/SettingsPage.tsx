import React, { useState } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Grid,
  TextField,
  Switch,
  FormControlLabel,
  Button,
  Divider,
  Alert,
  Tabs,
  Tab,
  useTheme,
} from '@mui/material';
import {
  Save as SaveIcon,
  Sync as SyncIcon,
  Notifications as NotificationsIcon,
  Security as SecurityIcon,
} from '@mui/icons-material';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

const TabPanel: React.FC<TabPanelProps> = ({ children, value, index }) => {
  return (
    <div role="tabpanel" hidden={value !== index}>
      {value === index && <Box sx={{ pt: 3 }}>{children}</Box>}
    </div>
  );
};

const SettingsPage: React.FC = () => {
  const theme = useTheme();
  const [tabValue, setTabValue] = useState(0);
  const [settings, setSettings] = useState({
    // General settings
    companyName: 'TechMac',
    timezone: 'Africa/Casablanca',
    language: 'fr',
    dateFormat: 'DD/MM/YYYY',
    
    // OneDrive sync settings
    oneDriveEnabled: true,
    syncInterval: 5,
    autoSync: true,
    
    // Notification settings
    emailNotifications: true,
    browserNotifications: true,
    deadlineReminders: true,
    weeklyReports: true,
    
    // Security settings
    sessionTimeout: 60,
    passwordExpiry: 90,
    twoFactorAuth: false,
  });

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleSave = () => {
    console.log('Settings saved:', settings);
    // Implementation for saving settings
  };

  const handleSettingChange = (key: string, value: any) => {
    setSettings(prev => ({ ...prev, [key]: value }));
  };

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" component="h1" fontWeight={700}>
          Paramètres
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Configurez les paramètres de l'application
        </Typography>
      </Box>

      <Card>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs value={tabValue} onChange={handleTabChange}>
            <Tab label="Général" />
            <Tab label="Synchronisation" />
            <Tab label="Notifications" />
            <Tab label="Sécurité" />
          </Tabs>
        </Box>

        <CardContent>
          {/* General Settings */}
          <TabPanel value={tabValue} index={0}>
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <TextField
                  label="Nom de l'entreprise"
                  fullWidth
                  value={settings.companyName}
                  onChange={(e) => handleSettingChange('companyName', e.target.value)}
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  label="Fuseau horaire"
                  fullWidth
                  value={settings.timezone}
                  onChange={(e) => handleSettingChange('timezone', e.target.value)}
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  label="Langue"
                  select
                  fullWidth
                  value={settings.language}
                  onChange={(e) => handleSettingChange('language', e.target.value)}
                  SelectProps={{ native: true }}
                >
                  <option value="fr">Français</option>
                  <option value="en">English</option>
                  <option value="ar">العربية</option>
                </TextField>
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  label="Format de date"
                  select
                  fullWidth
                  value={settings.dateFormat}
                  onChange={(e) => handleSettingChange('dateFormat', e.target.value)}
                  SelectProps={{ native: true }}
                >
                  <option value="DD/MM/YYYY">DD/MM/YYYY</option>
                  <option value="MM/DD/YYYY">MM/DD/YYYY</option>
                  <option value="YYYY-MM-DD">YYYY-MM-DD</option>
                </TextField>
              </Grid>
            </Grid>
          </TabPanel>

          {/* Sync Settings */}
          <TabPanel value={tabValue} index={1}>
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <Alert severity="info" sx={{ mb: 3 }}>
                  La synchronisation OneDrive permet de maintenir vos données à jour automatiquement.
                </Alert>
              </Grid>
              <Grid item xs={12}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={settings.oneDriveEnabled}
                      onChange={(e) => handleSettingChange('oneDriveEnabled', e.target.checked)}
                    />
                  }
                  label="Activer la synchronisation OneDrive"
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  label="Intervalle de synchronisation (minutes)"
                  type="number"
                  fullWidth
                  value={settings.syncInterval}
                  onChange={(e) => handleSettingChange('syncInterval', parseInt(e.target.value))}
                  disabled={!settings.oneDriveEnabled}
                />
              </Grid>
              <Grid item xs={12}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={settings.autoSync}
                      onChange={(e) => handleSettingChange('autoSync', e.target.checked)}
                    />
                  }
                  label="Synchronisation automatique"
                  disabled={!settings.oneDriveEnabled}
                />
              </Grid>
              <Grid item xs={12}>
                <Button
                  variant="outlined"
                  startIcon={<SyncIcon />}
                  disabled={!settings.oneDriveEnabled}
                >
                  Synchroniser maintenant
                </Button>
              </Grid>
            </Grid>
          </TabPanel>

          {/* Notification Settings */}
          <TabPanel value={tabValue} index={2}>
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <Typography variant="h6" gutterBottom>
                  Types de notifications
                </Typography>
              </Grid>
              <Grid item xs={12}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={settings.emailNotifications}
                      onChange={(e) => handleSettingChange('emailNotifications', e.target.checked)}
                    />
                  }
                  label="Notifications par email"
                />
              </Grid>
              <Grid item xs={12}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={settings.browserNotifications}
                      onChange={(e) => handleSettingChange('browserNotifications', e.target.checked)}
                    />
                  }
                  label="Notifications du navigateur"
                />
              </Grid>
              <Grid item xs={12}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={settings.deadlineReminders}
                      onChange={(e) => handleSettingChange('deadlineReminders', e.target.checked)}
                    />
                  }
                  label="Rappels d'échéance"
                />
              </Grid>
              <Grid item xs={12}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={settings.weeklyReports}
                      onChange={(e) => handleSettingChange('weeklyReports', e.target.checked)}
                    />
                  }
                  label="Rapports hebdomadaires"
                />
              </Grid>
            </Grid>
          </TabPanel>

          {/* Security Settings */}
          <TabPanel value={tabValue} index={3}>
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <Alert severity="warning" sx={{ mb: 3 }}>
                  Les paramètres de sécurité affectent tous les utilisateurs du système.
                </Alert>
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  label="Délai d'expiration de session (minutes)"
                  type="number"
                  fullWidth
                  value={settings.sessionTimeout}
                  onChange={(e) => handleSettingChange('sessionTimeout', parseInt(e.target.value))}
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  label="Expiration du mot de passe (jours)"
                  type="number"
                  fullWidth
                  value={settings.passwordExpiry}
                  onChange={(e) => handleSettingChange('passwordExpiry', parseInt(e.target.value))}
                />
              </Grid>
              <Grid item xs={12}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={settings.twoFactorAuth}
                      onChange={(e) => handleSettingChange('twoFactorAuth', e.target.checked)}
                    />
                  }
                  label="Authentification à deux facteurs"
                />
              </Grid>
            </Grid>
          </TabPanel>

          <Divider sx={{ my: 3 }} />

          {/* Save Button */}
          <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
            <Button
              variant="contained"
              startIcon={<SaveIcon />}
              onClick={handleSave}
              size="large"
            >
              Enregistrer les paramètres
            </Button>
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
};

export default SettingsPage;