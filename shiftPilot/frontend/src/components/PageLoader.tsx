import { Loader2 } from "lucide-react";

export function PageLoader() {
  return (
    <div className="flex items-center justify-center h-64 text-muted-foreground text-sm">
      <Loader2 size={18} className="animate-spin mr-2" />
      Loading…
    </div>
  );
}
