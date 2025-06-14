import React from 'react';
import {
  Card,
  CardHeader,
  CardContent,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Divider,
} from '@mui/material';
import {
  Add as AddIcon,
  Upload as UploadIcon,
  Download as DownloadIcon,
  Sync as SyncIcon,
  Assessment as ReportIcon,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';

const QuickActions: React.FC = () => {
  const navigate = useNavigate();

  const actions = [
    {
      id: 'create-task',
      label: 'Créer une Tâche',
      icon: <AddIcon />,
      action: () => navigate('/tasks/new'),
    },
    {
      id: 'import-excel',
      label: 'Importer Excel',
      icon: <UploadIcon />,
      action: () => navigate('/tasks/import'),
    },
    {
      id: 'export-data',
      label: 'Exporter Données',
      icon: <DownloadIcon />,
      action: () => navigate('/tasks/export'),
    },
    {
      id: 'sync-onedrive',
      label: 'Synchroniser OneDrive',
      icon: <SyncIcon />,
      action: () => {
        // Trigger sync
        console.log('Sync triggered');
      },
    },
    {
      id: 'generate-report',
      label: 'Générer Rapport',
      icon: <ReportIcon />,
      action: () => navigate('/analytics/reports'),
    },
  ];

  return (
    <Card>
      <CardHeader title="Actions Rapides" />
      <CardContent sx={{ p: 0 }}>
        <List>
          {actions.map((action, index) => (
            <React.Fragment key={action.id}>
              <ListItem disablePadding>
                <ListItemButton onClick={action.action}>
                  <ListItemIcon>{action.icon}</ListItemIcon>
                  <ListItemText primary={action.label} />
                </ListItemButton>
              </ListItem>
              {index < actions.length - 1 && <Divider />}
            </React.Fragment>
          ))}
        </List>
      </CardContent>
    </Card>
  );
};

export default QuickActions;