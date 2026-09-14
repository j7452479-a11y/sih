#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "TelemetryReceiver.h" // For FStructureSurveyInfo
#include "TacticalStructureSurveyor.generated.h"

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FOnStructureSurveyChanged, const FStructureSurveyInfo&, SurveyInfo);

/**
 * UTacticalStructureSurveyor
 * 
 * Production ActorComponent for Unreal Engine 5 Soldier Character or Drone.
 * Performs real-time raycast/aim surveying of buildings, bridges, bunkers, and obstacles,
 * extracting true physical dimensions (Length, Width, Height, Footprint Area, Sector, Clearance)
 * from mesh geometry and collision bounds, rendering 3D tactical reticles in world space.
 */
UCLASS(ClassGroup=(Custom), meta=(BlueprintSpawnableComponent))
class SIH_PERCEPTION_API UTacticalStructureSurveyor : public UActorComponent
{
    GENERATED_BODY()

public:
    UTacticalStructureSurveyor();

    /** Maximum distance in meters for the visor/camera line trace surveyor */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "SIH Surveyor")
    float MaxSurveyRangeMeters = 150.0f;

    /** Collision channel used for structure line tracing */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "SIH Surveyor")
    TEnumAsByte<ECollisionChannel> SurveyTraceChannel = ECC_Visibility;

    /** Whether to automatically trace from camera forward vector on each tick */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "SIH Surveyor")
    bool bContinuousAimSurvey = true;

    /** Render 3D tactical corner brackets and dimension labels in world space */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "SIH Surveyor")
    bool bDrawDebugReticles = true;

    /** Color for actively surveyed structure */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "SIH Surveyor")
    FColor ReticleColor = FColor(0, 240, 255); // Tactical Cyan

    /** Broadcast when a new structure is surveyed or survey target changes */
    UPROPERTY(BlueprintAssignable, Category = "SIH Surveyor")
    FOnStructureSurveyChanged OnStructureSurveyChanged;

    /** Currently surveyed structure data */
    UPROPERTY(BlueprintReadOnly, Category = "SIH Surveyor")
    FStructureSurveyInfo CurrentSurvey;

    /** True if a valid structure or obstacle is currently surveyed */
    UPROPERTY(BlueprintReadOnly, Category = "SIH Surveyor")
    bool bHasSurveyTarget = false;

    /**
     * Performs a forward trace from player camera/pawn view to survey target structure.
     * Computes real-world length, width, height, area, and clearances in meters.
     */
    UFUNCTION(BlueprintCallable, Category = "SIH Surveyor")
    bool SurveyAimTarget(FStructureSurveyInfo& OutInfo);

    /**
     * Inspects a specific actor and computes its real-world physical dimensions.
     */
    UFUNCTION(BlueprintCallable, Category = "SIH Surveyor")
    bool SurveyActor(AActor* TargetActor, FStructureSurveyInfo& OutInfo);

    /** Clears active survey state */
    UFUNCTION(BlueprintCallable, Category = "SIH Surveyor")
    void ClearSurvey();

protected:
    virtual void BeginPlay() override;
    virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

private:
    TWeakObjectPtr<AActor> LastSurveyedActor = nullptr;

    FString DetermineSector(const FVector& WorldLocationCm) const;
    float MeasureUnderpassClearance(AActor* BridgeActor, const FVector& SurfaceLocation) const;
    void DrawTacticalCornerBrackets(const FVector& Origin, const FVector& BoxExtent, const FColor& Color) const;
};
