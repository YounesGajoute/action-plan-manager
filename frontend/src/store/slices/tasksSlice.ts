import { createSlice, PayloadAction } from '@reduxjs/toolkit';

interface Task {
  id: string;
  po_number: string;
  action_description: string;
  customer: string;
  requester: string;
  responsible: string;
  category?: string;
  status: string;
  priority: string;
  deadline?: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

interface TaskCounts {
  total: number;
  pending: number;
  inProgress: number;
  completed: number;
  overdue: number;
  byCategory: {
    installation: number;
    reparation: number;
    developpement: number;
    livraison: number;
    commercial: number;
  };
}

interface TasksState {
  tasks: Task[];
  taskCounts: TaskCounts | null;
  selectedTask: Task | null;
  loading: boolean;
  error: string | null;
  filters: {
    status?: string;
    category?: string;
    responsible?: string;
    dateRange?: [string, string];
  };
}

const initialState: TasksState = {
  tasks: [],
  taskCounts: null,
  selectedTask: null,
  loading: false,
  error: null,
  filters: {},
};

const tasksSlice = createSlice({
  name: 'tasks',
  initialState,
  reducers: {
    setTasks: (state, action: PayloadAction<Task[]>) => {
      state.tasks = action.payload;
    },
    setTaskCounts: (state, action: PayloadAction<TaskCounts>) => {
      state.taskCounts = action.payload;
    },
    setSelectedTask: (state, action: PayloadAction<Task | null>) => {
      state.selectedTask = action.payload;
    },
    addTask: (state, action: PayloadAction<Task>) => {
      state.tasks.unshift(action.payload);
    },
    updateTask: (state, action: PayloadAction<Task>) => {
      const index = state.tasks.findIndex(task => task.id === action.payload.id);
      if (index !== -1) {
        state.tasks[index] = action.payload;
      }
    },
    deleteTask: (state, action: PayloadAction<string>) => {
      state.tasks = state.tasks.filter(task => task.id !== action.payload);
    },
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.loading = action.payload;
    },
    setError: (state, action: PayloadAction<string>) => {
      state.error = action.payload;
    },
    setFilters: (state, action: PayloadAction<TasksState['filters']>) => {
      state.filters = { ...state.filters, ...action.payload };
    },
  },
});

export const {
  setTasks,
  setTaskCounts,
  setSelectedTask,
  addTask,
  updateTask,
  deleteTask,
  setLoading,
  setError,
  setFilters,
} = tasksSlice.actions;
export default tasksSlice.reducer;