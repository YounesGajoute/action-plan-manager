import React from 'react';
import {
  Grid,
  Card,
  CardHeader,
  CardContent,
  Box,
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
  AreaChart,
  Area,
} from 'recharts';

interface ChartsSectionProps {
  data: any;
}

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8'];

const ChartsSection: React.FC<ChartsSectionProps> = ({ data }) => {
  const theme = useTheme();

  // Mock data if no data provided
  const chartData = data || {
    categoryDistribution: [
      { category: 'Installation', count: 23, percentage: 35 },
      { category: 'Réparation', count: 18, percentage: 27 },
      { category: 'Développement', count: 15, percentage: 23 },
      { category: 'Livraison', count: 8, percentage: 12 },
      { category: 'Commercial', count: 2, percentage: 3 },
    ],
    weeklyProgress: [
      { date: 'Lun', created: 12, completed: 8 },
      { date: 'Mar', created: 15, completed: 12 },
      { date: 'Mer', created: 10, completed: 14 },
      { date: 'Jeu', created: 18, completed: 11 },
      { date: 'Ven', created: 14, completed: 16 },
      { date: 'Sam', created: 5, completed: 8 },
      { date: 'Dim', created: 3, completed: 5 },
    ]
  };

  return (
    <Grid container spacing={3}>
      {/* Category Distribution Pie Chart */}
      <Grid item xs={12} md={6}>
        <Card>
          <CardHeader title="Répartition par Catégorie" />
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={chartData.categoryDistribution}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ category, percentage }) => `${category} ${percentage}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="count"
                >
                  {chartData.categoryDistribution.map((entry: any, index: number) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </Grid>

      {/* Weekly Progress Chart */}
      <Grid item xs={12} md={6}>
        <Card>
          <CardHeader title="Progression Hebdomadaire" />
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={chartData.weeklyProgress}>
                <defs>
                  <linearGradient id="colorCreated" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={theme.palette.primary.main} stopOpacity={0.8}/>
                    <stop offset="95%" stopColor={theme.palette.primary.main} stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="colorCompleted" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={theme.palette.success.main} stopOpacity={0.8}/>
                    <stop offset="95%" stopColor={theme.palette.success.main} stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <XAxis dataKey="date" />
                <YAxis />
                <CartesianGrid strokeDasharray="3 3" />
                <Tooltip />
                <Area
                  type="monotone"
                  dataKey="created"
                  stackId="1"
                  stroke={theme.palette.primary.main}
                  fill="url(#colorCreated)"
                  name="Créées"
                />
                <Area
                  type="monotone"
                  dataKey="completed"
                  stackId="1"
                  stroke={theme.palette.success.main}
                  fill="url(#colorCompleted)"
                  name="Terminées"
                />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </Grid>

      {/* Task Completion Trend */}
      <Grid item xs={12}>
        <Card>
          <CardHeader title="Tendance de Complétion des Tâches" />
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={chartData.weeklyProgress}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Line
                  type="monotone"
                  dataKey="completed"
                  stroke={theme.palette.success.main}
                  strokeWidth={3}
                  dot={{ fill: theme.palette.success.main, strokeWidth: 2, r: 4 }}
                  name="Tâches Terminées"
                />
                <Line
                  type="monotone"
                  dataKey="created"
                  stroke={theme.palette.primary.main}
                  strokeWidth={3}
                  dot={{ fill: theme.palette.primary.main, strokeWidth: 2, r: 4 }}
                  name="Tâches Créées"
                />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );
};

export default ChartsSection;