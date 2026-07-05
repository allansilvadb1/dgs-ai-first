import { z } from 'zod';

export const feedbackSchema = z.object({
  queryId: z.string().min(1, 'queryId não pode ser vazio'),
  rating: z.number().int().min(1).max(5),
  comment: z.string().max(500).optional(),
  attendantEmail: z.string().email('attendantEmail deve ser um e-mail válido'),
});

export type FeedbackInput = z.infer<typeof feedbackSchema>;
