import React, { useState } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Grid,
  TextField,
  Button,
  Avatar,
  Divider,
  Alert,
  useTheme,
} from '@mui/material';
import { Save as SaveIcon, PhotoCamera as PhotoCameraIcon } from '@mui/icons-material';
import { useAppSelector } from '../hooks/redux';

const ProfilePage: React.FC = () => {
  const theme = useTheme();
  const { user } = useAppSelector((state) => state.auth);
  const [profile, setProfile] = useState({
    name: user?.name || '',
    email: user?.email || '',
    phone: '',
    department: '',
    position: '',
    location: 'Casablanca, Maroc',
  });

  const handleSave = () => {
    console.log('Profile saved:', profile);
    // Implementation for saving profile
  };

  const handleInputChange = (field: string, value: string) => {
    setProfile(prev => ({ ...prev, [field]: value }));
  };

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" component="h1" fontWeight={700}>
          Mon Profil
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Gérez vos informations personnelles et préférences
        </Typography>
      </Box>

      <Grid container spacing={3}>
        {/* Profile Info Card */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent sx={{ textAlign: 'center' }}>
              <Avatar
                sx={{
                  width: 120,
                  height: 120,
                  fontSize: '3rem',
                  bgcolor: theme.palette.primary.main,
                  mx: 'auto',
                  mb: 2,
                }}
              >
                {user?.name?.charAt(0).toUpperCase() || 'U'}
              </Avatar>
              <Button
                variant="outlined"
                startIcon={<PhotoCameraIcon />}
                size="small"
                sx={{ mb: 2 }}
              >
                Changer Photo
              </Button>
              <Typography variant="h6" fontWeight={600}>
                {profile.name}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {profile.email}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {profile.position || 'Poste non défini'}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* Profile Form */}
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom fontWeight={600}>
                Informations Personnelles
              </Typography>
              
              <Grid container spacing={3}>
                <Grid item xs={12} sm={6}>
                  <TextField
                    label="Nom complet"
                    fullWidth
                    value={profile.name}
                    onChange={(e) => handleInputChange('name', e.target.value)}
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    label="Email"
                    type="email"
                    fullWidth
                    value={profile.email}
                    onChange={(e) => handleInputChange('email', e.target.value)}
                    disabled
                    helperText="L'email ne peut pas être modifié"
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    label="Téléphone"
                    fullWidth
                    value={profile.phone}
                    onChange={(e) => handleInputChange('phone', e.target.value)}
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    label="Département"
                    fullWidth
                    value={profile.department}
                    onChange={(e) => handleInputChange('department', e.target.value)}
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    label="Poste"
                    fullWidth
                    value={profile.position}
                    onChange={(e) => handleInputChange('position', e.target.value)}
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    label="Localisation"
                    fullWidth
                    value={profile.location}
                    onChange={(e) => handleInputChange('location', e.target.value)}
                  />
                </Grid>
              </Grid>

              <Divider sx={{ my: 3 }} />

              <Typography variant="h6" gutterBottom fontWeight={600}>
                Sécurité
              </Typography>
              
              <Alert severity="info" sx={{ mb: 2 }}>
                La gestion des mots de passe se fait via Microsoft 365. 
                Utilisez le portail Microsoft pour modifier votre mot de passe.
              </Alert>

              <Button variant="outlined" sx={{ mr: 2 }}>
                Changer le mot de passe
              </Button>
              <Button variant="outlined">
                Gérer la sécurité
              </Button>

              <Divider sx={{ my: 3 }} />

              <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
                <Button
                  variant="contained"
                  startIcon={<SaveIcon />}
                  onClick={handleSave}
                  size="large"
                >
                  Enregistrer les modifications
                </Button>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default ProfilePage;