import { z } from 'zod';

/**
 * Schema de validação para o request do endpoint de query
 * Valida que a pergunta é uma string não-vazia entre 1 e 1000 caracteres
 */
export const RequestSchema = z.object({
  question: z
    .string({ errorMap: () => ({ message: 'question must be a string' }) })
    .min(1, { message: 'question cannot be empty' })
    .max(1000, { message: 'question must not exceed 1000 characters' }),
});

/**
 * Schema de validação para o response do endpoint de query
 * Valida que a resposta contém answer (non-empty) e source_documents (array de strings)
 */
export const ResponseSchema = z.object({
  answer: z
    .string({ errorMap: () => ({ message: 'answer must be a string' }) })
    .min(1, { message: 'answer cannot be empty' }),
  source_documents: z
    .array(z.string(), {
      errorMap: () => ({ message: 'source_documents must be an array of strings' }),
    })
    .default([]),
});

/**
 * Tipos TypeScript inferidos automaticamente dos schemas Zod
 */
export type QueryRequest = z.infer<typeof RequestSchema>;
export type QueryResponse = z.infer<typeof ResponseSchema>;
