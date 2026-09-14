#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "Networking.h"
#include "Sockets.h"
#include "TelemetryReceiver.generated.h"

USTRUCT(BlueprintType)
struct FTrackedTargetInfo
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadOnly, Category = "SIH Telemetry")
    int32 TargetId = 0;

    UPROPERTY(BlueprintReadOnly, Category = "SIH Telemetry")
    FVector WorldLocation = FVector::ZeroVector;

    UPROPERTY(BlueprintReadOnly, Category = "SIH Telemetry")
    float Speed = 0.0f;

    UPROPERTY(BlueprintReadOnly, Category = "SIH Telemetry")
    float Heading = 0.0f;

    UPROPERTY(BlueprintReadOnly, Category = "SIH Telemetry")
    FString State = TEXT("CONFIRMED");
};

USTRUCT(BlueprintType)
struct FStructureSurveyInfo
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadOnly, Category = "SIH Structure Surveyor")
    FString StructureId = TEXT("");

    UPROPERTY(BlueprintReadOnly, Category = "SIH Structure Surveyor")
    FString StructureName = TEXT("Unknown Structure");

    UPROPERTY(BlueprintReadOnly, Category = "SIH Structure Surveyor")
    FString StructureType = TEXT("Building");

    UPROPERTY(BlueprintReadOnly, Category = "SIH Structure Surveyor")
    FVector WorldLocation = FVector::ZeroVector; // In Unreal centimeters

    UPROPERTY(BlueprintReadOnly, Category = "SIH Structure Surveyor")
    float LengthMeters = 0.0f;

    UPROPERTY(BlueprintReadOnly, Category = "SIH Structure Surveyor")
    float WidthMeters = 0.0f;

    UPROPERTY(BlueprintReadOnly, Category = "SIH Structure Surveyor")
    float HeightMeters = 0.0f;

    UPROPERTY(BlueprintReadOnly, Category = "SIH Structure Surveyor")
    float FootprintAreaSqM = 0.0f;

    UPROPERTY(BlueprintReadOnly, Category = "SIH Structure Surveyor")
    FString Sector = TEXT("");

    UPROPERTY(BlueprintReadOnly, Category = "SIH Structure Surveyor")
    float ClearanceMeters = 0.0f;

    UPROPERTY(BlueprintReadOnly, Category = "SIH Structure Surveyor")
    bool bIsUnderpass = false;

    UPROPERTY(BlueprintReadOnly, Category = "SIH Structure Surveyor")
    bool bIsActive = false;
};

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FOnTelemetryUpdated, const TArray<FTrackedTargetInfo>&, Targets);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FOnStructureDesignated, const FStructureSurveyInfo&, StructureInfo);

UCLASS(ClassGroup=(Custom), meta=(BlueprintSpawnableComponent))
class SIH_PERCEPTION_API UTelemetryReceiver : public UActorComponent
{
    GENERATED_BODY()

public:
    UTelemetryReceiver();

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "SIH Network")
    int32 ListenPort = 5003;

    UPROPERTY(BlueprintAssignable, Category = "SIH Telemetry")
    FOnTelemetryUpdated OnTelemetryUpdated;

    UPROPERTY(BlueprintAssignable, Category = "SIH Telemetry")
    FOnStructureDesignated OnStructureDesignated;

    UPROPERTY(BlueprintReadOnly, Category = "SIH Telemetry")
    TArray<FTrackedTargetInfo> ActiveTargets;

    UPROPERTY(BlueprintReadOnly, Category = "SIH Telemetry")
    FStructureSurveyInfo DesignatedStructure;

    UPROPERTY(BlueprintReadOnly, Category = "SIH Telemetry")
    bool bHasDesignatedStructure = false;

protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
    virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

private:
    FSocket* ListenSocket = nullptr;
    void ReadIncomingPackets();
};
