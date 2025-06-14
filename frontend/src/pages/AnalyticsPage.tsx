import React, { useState } from 'react';
import {
  Box,
  Typography,
  Grid,
  Card,
  CardHeader,
  CardContent,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Button,
  useTheme,
} from '@mui/material';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
  Area,
  AreaChart,
} from 'recharts';
import { Download as DownloadIcon } from '@mui/icons-material';
import { useAnalytics } from '../hooks/useAnalytics';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8'];

const AnalyticsPage: React.FC = () => {
  const theme = useTheme();
  const { dashboardData, loading } = useAnalytics();
  const [timeRange, setTimeRange] = useState('month');

  // Mock data for charts
  const categoryData = [
    { name: 'Installation', value: 23, color: COLORS[0] },
    { name: 'Réparation', value: 45, color: COLORS[1] },
    { name: 'Développement', value: 12, color: COLORS[2] },
    { name: 'Livraison', value: 8, color: COLORS[3] },
    { name: 'Commercial', value: 15, color: COLORS[4] },
  ];

  const performanceData = [
    { month: 'Jan', completed: 20, created: 25 },
    { month: 'Fév', completed: 32, created: 30 },
    { month: 'Mar', completed: 28, created: 35 },
    { month: 'Avr', completed: 45, created: 40 },
    { month: 'Mai', completed: 38, created: 42 },
    { month: 'Jun', completed: 52, created: 50 },
  ];

  const weeklyTrendData = [
    { day: 'Lun', tasks: 12 },
    { day: 'Mar', tasks: 19 },
    { day: 'Mer', tasks: 15 },
    { day: 'Jeu', tasks: 25 },
    { day: 'Ven', tasks: 22 },
    { day: 'Sam', tasks: 8 },
    { day: 'Dim', tasks: 5 },
  ];

  const teamPerformanceData = [
    { name: 'Amine', completed: 45, pending: 12 },
    { name: 'Hassan', completed: 38, pending: 8 },
    { name: 'Youssef', completed: 52, pending: 15 },
    { name: 'Omar', completed: 32, pending: 6 },
    { name: 'Karim', completed: 28, pending: 10 },
  ];

  const handleExportReport = () => {
    // Implementation for report export
    console.log('Exporting report...');
  };

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" component="h1" fontWeight={700}>
            Analyses et Rapports
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Visualisez les performances et tendances de vos tâches
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Période</InputLabel>
            <Select
              value={timeRange}
              label="Période"
              onChange={(e) => setTimeRange(e.target.value)}
            >
              <MenuItem value="week">Cette semaine</MenuItem>
              <MenuItem value="month">Ce mois</MenuItem>
              <MenuItem value="quarter">Ce trimestre</MenuItem>
              <MenuItem value="year">Cette année</MenuItem>
            </Select>
          </FormControl>
          <Button
            variant="outlined"
            startIcon={<DownloadIcon />}
            onClick={handleExportReport}
          >
            Exporter
          </Button>
        </Box>
      </Box>

      {/* Charts Grid */}
      <Grid container spacing={3}>
        {/* Category Distribution */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardHeader title="Répartition par Catégorie" />
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={categoryData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {categoryData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>

        {/* Weekly Trend */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardHeader title="Tendance Hebdomadaire" />
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={weeklyTrendData}>
                  <defs>
                    <linearGradient id="colorTasks" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={theme.palette.primary.main} stopOpacity={0.8}/>
                      <stop offset="95%" stopColor={theme.palette.primary.main} stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="day" />
                  <YAxis />
                  <CartesianGrid strokeDasharray="3 3" />
                  <Tooltip />
                  <Area
                    type="monotone"
                    dataKey="tasks"
                    stroke={theme.palette.primary.main}
                    fillOpacity={1}
                    fill="url(#colorTasks)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>

        {/* Performance Comparison */}
        <Grid item xs={12}>
          <Card>
            <CardHeader title="Performance Mensuelle" />
            <CardContent>
              <ResponsiveContainer width="100%" height={400}>
                <BarChart data={performanceData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="created" fill={theme.palette.primary.main} name="Créées" />
                  <Bar dataKey="completed" fill={theme.palette.success.main} name="Terminées" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>

        {/* Team Performance */}
        <Grid item xs={12}>
          <Card>
            <CardHeader title="Performance par Équipe" />
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={teamPerformanceData} layout="horizontal">
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis type="number" />
                  <YAxis dataKey="name" type="category" width={80} />
                  <Tooltip />
                  <Bar dataKey="completed" fill={theme.palette.success.main} name="Terminées" />
                  <Bar dataKey="pending" fill={theme.palette.warning.main} name="En attente" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default AnalyticsPage;