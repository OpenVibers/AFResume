import { defineCollection, z } from 'astro:content';

const experience = defineCollection({
  type: 'data',
  schema: z.object({
    company: z.string(),
    role: z.string(),
    start: z.string(),
    end: z.string(),
    location: z.string().optional(),
    bullets: z.array(z.string()),
    stack: z.array(z.string()).default([]),
    featured: z.boolean().default(false),
    order: z.number().default(0),
  }),
});

const projects = defineCollection({
  type: 'content',
  schema: z.object({
    title: z.string(),
    category: z.enum(['amazon', 'hobo', 'python', 'game', 'hardware', 'web', '3d', 'tools']),
    summary: z.string(),
    tech: z.array(z.string()).default([]),
    role: z.string().optional(),
    year: z.string().optional(),
    image: z.string().optional(),
    images: z.array(z.string()).default([]),
    links: z.object({
      live: z.string().url().optional(),
      repo: z.string().url().optional(),
      video: z.string().url().optional(),
    }).default({}),
    featured: z.boolean().default(false),
    order: z.number().default(0),
  }),
});

const skills = defineCollection({
  type: 'data',
  schema: z.object({
    group: z.string(),
    items: z.array(z.object({
      name: z.string(),
      level: z.enum(['core', 'strong', 'familiar']).optional(),
    })),
    order: z.number().default(0),
  }),
});

export const collections = { experience, projects, skills };
