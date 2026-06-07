export interface EventFilterOption {
  active: boolean;
  label: string;
  value: string;
}

export interface EventFilterGroup {
  key: string;
  label: string;
  options: readonly EventFilterOption[];
}
