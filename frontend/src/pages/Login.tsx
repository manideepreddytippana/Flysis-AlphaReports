import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useNavigate } from "react-router";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";

export default function Login() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const loginMutation = useMutation({
    mutationFn: () => api.auth.devLogin(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["auth", "me"] });
      navigate("/");
    },
  });

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0b0f19]">
      <Card className="w-full max-w-sm bg-[#121828] border-[#1b1f2a] text-[#d0e7f4]">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl font-bold">ResearchLens</CardTitle>
          <p className="text-sm text-[#64748b]">Local Development Mode</p>
        </CardHeader>
        <CardContent>
          <Button
            className="w-full bg-[#00e1b7] text-[#0b0f19] hover:bg-[#00e1b7]/90 font-semibold"
            size="lg"
            onClick={() => loginMutation.mutate()}
            disabled={loginMutation.isPending}
          >
            {loginMutation.isPending ? "Signing in..." : "Continue as Dev User"}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
