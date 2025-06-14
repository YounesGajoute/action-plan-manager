import React from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  Avatar,
  Container,
  useTheme,
  alpha,
} from '@mui/material';
import { Microsoft as MicrosoftIcon } from '@mui/icons-material';
import { useMsal } from '@azure/msal-react';
import { loginRequest } from '../../config/authConfig';

const LoginPage: React.FC = () => {
  const theme = useTheme();
  const { instance } = useMsal();

  const handleLogin = async () => {
    try {
      await instance.loginRedirect(loginRequest);
    } catch (error) {
      console.error('Login error:', error);
    }
  };

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: `linear-gradient(135deg, ${theme.palette.primary.main} 0%, ${theme.palette.secondary.main} 100%)`,
        position: 'relative',
        '&::before': {
          content: '""',
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'url(/pattern.svg) repeat',
          opacity: 0.1,
        }
      }}
    >
      <Container maxWidth="sm">
        <Paper
          elevation={24}
          sx={{
            p: 4,
            borderRadius: 3,
            backdropFilter: 'blur(10px)',
            background: alpha(theme.palette.background.paper, 0.9),
            border: `1px solid ${alpha(theme.palette.common.white, 0.2)}`,
          }}
        >
          <Box sx={{ textAlign: 'center', mb: 4 }}>
            <Avatar
              sx={{
                width: 80,
                height: 80,
                bgcolor: theme.palette.primary.main,
                mx: 'auto',
                mb: 2,
                fontSize: '2rem',
                fontWeight: 'bold',
              }}
            >
              AP
            </Avatar>
            <Typography
              variant="h3"
              component="h1"
              sx={{
                fontWeight: 700,
                mb: 1,
                background: `linear-gradient(45deg, ${theme.palette.primary.main}, ${theme.palette.secondary.main})`,
                backgroundClip: 'text',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
              }}
            >
              Action Plan
            </Typography>
            <Typography
              variant="h6"
              color="text.secondary"
              sx={{ mb: 3 }}
            >
              Management System
            </Typography>
            <Typography
              variant="body1"
              color="text.secondary"
              sx={{ mb: 4 }}
            >
              Connectez-vous avec votre compte Microsoft 365 pour accéder au système de gestion des plans d'action.
            </Typography>
          </Box>

          <Button
            fullWidth
            variant="contained"
            size="large"
            startIcon={<MicrosoftIcon />}
            onClick={handleLogin}
            sx={{
              py: 1.5,
              fontSize: '1.1rem',
              fontWeight: 600,
              background: `linear-gradient(45deg, ${theme.palette.primary.main}, ${theme.palette.primary.dark})`,
              '&:hover': {
                background: `linear-gradient(45deg, ${theme.palette.primary.dark}, ${theme.palette.primary.main})`,
                transform: 'translateY(-2px)',
                boxShadow: theme.shadows[8],
              },
              transition: 'all 0.3s ease',
            }}
          >
            Se connecter avec Microsoft 365
          </Button>

          <Typography
            variant="caption"
            color="text.secondary"
            sx={{
              display: 'block',
              textAlign: 'center',
              mt: 3,
              px: 2,
            }}
          >
            En vous connectant, vous acceptez nos conditions d'utilisation et notre politique de confidentialité.
          </Typography>
        </Paper>
      </Container>
    </Box>
  );
};

export default LoginPage;