import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  Grid,
  MenuItem,
  Box,
  Typography,
  Alert,
} from '@mui/material';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { useForm, Controller } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as yup from 'yup';
import { Task, TaskStatus, TaskPriority } from '../../types/task';
import { TASK_STATUSES, TASK_PRIORITIES, TASK_CATEGORIES } from '../../utils/constants';

interface TaskFormProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (data: Partial<Task>) => Promise<void>;
  task?: Task | null;
  loading?: boolean;
}

// Validation schema
const taskSchema = yup.object({
  po_number: yup.string().optional(),
  action_description: yup.string().required('La description de l\'action est requise'),
  customer: yup.string().required('Le client est requis'),
  requester: yup.string().required('Le demandeur est requis'),
  responsible: yup.string().required('Le responsable est requis'),
  category: yup.string().optional(),
  status: yup.string().required('Le statut est requis'),
  priority: yup.string().optional(),
  deadline: yup.date().optional().nullable(),
  notes: yup.string().optional(),
});

type TaskFormData = yup.InferType<typeof taskSchema>;

const TaskForm: React.FC<TaskFormProps> = ({
  open,
  onClose,
  onSubmit,
  task,
  loading = false,
}) => {
  const [submitError, setSubmitError] = useState<string | null>(null);

  const {
    control,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<TaskFormData>({
    resolver: yupResolver(taskSchema),
    defaultValues: {
      po_number: '',
      action_description: '',
      customer: '',
      requester: '',
      responsible: '',
      category: '',
      status: TASK_STATUSES.PENDING,
      priority: TASK_PRIORITIES.MEDIUM,
      deadline: null,
      notes: '',
    },
  });

  // Reset form when task changes
  useEffect(() => {
    if (task) {
      reset({
        po_number: task.po_number || '',
        action_description: task.action_description || '',
        customer: task.customer || '',
        requester: task.requester || '',
        responsible: task.responsible || '',
        category: task.category || '',
        status: task.status || TASK_STATUSES.PENDING,
        priority: task.priority || TASK_PRIORITIES.MEDIUM,
        deadline: task.deadline ? new Date(task.deadline) : null,
        notes: task.notes || '',
      });
    } else {
      reset({
        po_number: '',
        action_description: '',
        customer: '',
        requester: '',
        responsible: '',
        category: '',
        status: TASK_STATUSES.PENDING,
        priority: TASK_PRIORITIES.MEDIUM,
        deadline: null,
        notes: '',
      });
    }
  }, [task, reset]);

  const handleFormSubmit = async (data: TaskFormData) => {
    try {
      setSubmitError(null);
      await onSubmit({
        ...data,
        deadline: data.deadline ? data.deadline.toISOString() : undefined,
      });
      onClose();
    } catch (error) {
      setSubmitError(
        error instanceof Error ? error.message : 'Erreur lors de la sauvegarde'
      );
    }
  };

  const handleClose = () => {
    setSubmitError(null);
    onClose();
  };

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: { borderRadius: 2 }
      }}
    >
      <DialogTitle>
        <Typography variant="h6" fontWeight={600}>
          {task ? 'Modifier la Tâche' : 'Nouvelle Tâche'}
        </Typography>
      </DialogTitle>

      <form onSubmit={handleSubmit(handleFormSubmit)}>
        <DialogContent>
          {submitError && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {submitError}
            </Alert>
          )}

          <Grid container spacing={3}>
            {/* PO Number */}
            <Grid item xs={12} sm={6}>
              <Controller
                name="po_number"
                control={control}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label="Numéro PO"
                    fullWidth
                    error={!!errors.po_number}
                    helperText={errors.po_number?.message}
                  />
                )}
              />
            </Grid>

            {/* Category */}
            <Grid item xs={12} sm={6}>
              <Controller
                name="category"
                control={control}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label="Catégorie"
                    select
                    fullWidth
                    error={!!errors.category}
                    helperText={errors.category?.message}
                  >
                    <MenuItem value="">Aucune</MenuItem>
                    {Object.values(TASK_CATEGORIES).map((category) => (
                      <MenuItem key={category} value={category}>
                        {category}
                      </MenuItem>
                    ))}
                  </TextField>
                )}
              />
            </Grid>

            {/* Action Description */}
            <Grid item xs={12}>
              <Controller
                name="action_description"
                control={control}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label="Description de l'Action *"
                    fullWidth
                    multiline
                    rows={3}
                    error={!!errors.action_description}
                    helperText={errors.action_description?.message}
                  />
                )}
              />
            </Grid>

            {/* Customer */}
            <Grid item xs={12} sm={6}>
              <Controller
                name="customer"
                control={control}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label="Client *"
                    fullWidth
                    error={!!errors.customer}
                    helperText={errors.customer?.message}
                  />
                )}
              />
            </Grid>

            {/* Requester */}
            <Grid item xs={12} sm={6}>
              <Controller
                name="requester"
                control={control}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label="Demandeur *"
                    fullWidth
                    error={!!errors.requester}
                    helperText={errors.requester?.message}
                  />
                )}
              />
            </Grid>

            {/* Responsible */}
            <Grid item xs={12} sm={6}>
              <Controller
                name="responsible"
                control={control}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label="Responsable *"
                    fullWidth
                    error={!!errors.responsible}
                    helperText={errors.responsible?.message}
                  />
                )}
              />
            </Grid>

            {/* Status */}
            <Grid item xs={12} sm={6}>
              <Controller
                name="status"
                control={control}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label="Statut *"
                    select
                    fullWidth
                    error={!!errors.status}
                    helperText={errors.status?.message}
                  >
                    {Object.values(TASK_STATUSES).map((status) => (
                      <MenuItem key={status} value={status}>
                        {status}
                      </MenuItem>
                    ))}
                  </TextField>
                )}
              />
            </Grid>

            {/* Priority */}
            <Grid item xs={12} sm={6}>
              <Controller
                name="priority"
                control={control}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label="Priorité"
                    select
                    fullWidth
                    error={!!errors.priority}
                    helperText={errors.priority?.message}
                  >
                    {Object.values(TASK_PRIORITIES).map((priority) => (
                      <MenuItem key={priority} value={priority}>
                        {priority}
                      </MenuItem>
                    ))}
                  </TextField>
                )}
              />
            </Grid>

            {/* Deadline */}
            <Grid item xs={12} sm={6}>
              <Controller
                name="deadline"
                control={control}
                render={({ field }) => (
                  <DatePicker
                    label="Échéance"
                    value={field.value}
                    onChange={field.onChange}
                    renderInput={(params) => (
                      <TextField
                        {...params}
                        fullWidth
                        error={!!errors.deadline}
                        helperText={errors.deadline?.message}
                      />
                    )}
                  />
                )}
              />
            </Grid>

            {/* Notes */}
            <Grid item xs={12}>
              <Controller
                name="notes"
                control={control}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label="Notes"
                    fullWidth
                    multiline
                    rows={3}
                    error={!!errors.notes}
                    helperText={errors.notes?.message}
                  />
                )}
              />
            </Grid>
          </Grid>
        </DialogContent>

        <DialogActions sx={{ p: 3, pt: 0 }}>
          <Button onClick={handleClose} disabled={isSubmitting}>
            Annuler
          </Button>
          <Button
            type="submit"
            variant="contained"
            disabled={isSubmitting || loading}
            sx={{ minWidth: 120 }}
          >
            {isSubmitting ? 'Sauvegarde...' : task ? 'Modifier' : 'Créer'}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
};

export default TaskForm;