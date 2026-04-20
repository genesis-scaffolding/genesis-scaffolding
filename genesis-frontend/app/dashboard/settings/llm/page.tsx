import { getLLMConfigAction } from "@/app/actions/llm-config";
import { GeneralSettingsCard } from "@/components/dashboard/llm/general-settings-card";
import { ProviderSection } from "@/components/dashboard/llm/provider-section";
import { ModelSection } from "@/components/dashboard/llm/model-section";

export default async function LLMSettingsPage() {
  const config = await getLLMConfigAction();

  return (
    <div className="space-y-10 animate-in fade-in duration-500">
      <section className="space-y-4">
        <div>
          <h2 className="text-lg font-medium">Default Model</h2>
          <p className="text-sm text-muted-foreground">
            Select the primary model used for chat and background tasks.
          </p>
        </div>
        <GeneralSettingsCard
          defaultModel={config.default_model}
          models={Object.keys(config.models)}
        />
      </section>

      <section className="space-y-4">
        <div>
          <h2 className="text-lg font-medium">Providers</h2>
          <p className="text-sm text-muted-foreground">
            Configure external API access like OpenRouter or OpenAI.
          </p>
        </div>
        <ProviderSection providers={config.providers} />
      </section>

      <section className="space-y-4">
        <div>
          <h2 className="text-lg font-medium">Models</h2>
          <p className="text-sm text-muted-foreground">
            Define specific model versions and their inference parameters.
          </p>
        </div>
        <ModelSection
          models={config.models}
          providers={Object.keys(config.providers)}
        />
      </section>
    </div>
  );
}
