export type OneCodeMetadata = {
  workspace?: string;
};

export function buildOneCodeModelKwargs(
  modelKwargs: Record<string, unknown> | undefined,
  metadata: OneCodeMetadata | undefined,
): Record<string, unknown> | undefined {
  const workspace = typeof metadata?.workspace === 'string' ? metadata.workspace.trim() : '';
  if (!workspace) {
    return modelKwargs;
  }

  return {
    ...(modelKwargs ?? {}),
    metadata: {
      ...((modelKwargs?.metadata && typeof modelKwargs.metadata === 'object'
        ? modelKwargs.metadata
        : {}) as Record<string, unknown>),
      workspace,
    },
  };
}
