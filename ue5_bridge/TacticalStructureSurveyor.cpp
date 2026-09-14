#include "TacticalStructureSurveyor.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "DrawDebugHelpers.h"
#include "PhysicalMaterials/PhysicalMaterial.h"

UTacticalStructureSurveyor::UTacticalStructureSurveyor()
{
    PrimaryComponentTick.bCanEverTick = true;
}

void UTacticalStructureSurveyor::BeginPlay()
{
    Super::BeginPlay();
}

void UTacticalStructureSurveyor::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
    Super::TickComponent(DeltaTime, TickType, ThisTickFunction);

    if (bContinuousAimSurvey)
    {
        SurveyAimTarget(CurrentSurvey);
    }
}

bool UTacticalStructureSurveyor::SurveyAimTarget(FStructureSurveyInfo& OutInfo)
{
    if (!GetWorld() || !GetOwner()) return false;

    FVector TraceStart = GetOwner()->GetActorLocation();
    FRotator TraceRot = GetOwner()->GetActorRotation();

    // If attached to a pawn with a controller, use player camera view point
    if (APawn* OwnerPawn = Cast<APawn>(GetOwner()))
    {
        if (AController* Controller = OwnerPawn->GetController())
        {
            Controller->GetPlayerViewPoint(TraceStart, TraceRot);
        }
    }

    FVector TraceEnd = TraceStart + (TraceRot.Vector() * (MaxSurveyRangeMeters * 100.0f));

    FCollisionQueryParams Params(FName(TEXT("SurveyTrace")), true, GetOwner());
    Params.bReturnPhysicalMaterial = true;

    FHitResult Hit;
    if (GetWorld()->LineTraceSingleByChannel(Hit, TraceStart, TraceEnd, SurveyTraceChannel, Params))
    {
        AActor* HitActor = Hit.GetActor();
        if (HitActor && HitActor != GetOwner())
        {
            // Ignore terrain landscape actors
            FString ClassName = HitActor->GetClass()->GetName();
            if (!ClassName.Contains(TEXT("Landscape")) && !ClassName.Contains(TEXT("Terrain")))
            {
                return SurveyActor(HitActor, OutInfo);
            }
        }
    }

    if (bHasSurveyTarget)
    {
        ClearSurvey();
    }
    return false;
}

bool UTacticalStructureSurveyor::SurveyActor(AActor* TargetActor, FStructureSurveyInfo& OutInfo)
{
    if (!TargetActor || !GetWorld()) return false;

    // 1. Extract 3D World Bounds
    FVector Origin, BoxExtent;
    TargetActor->GetActorBounds(false, Origin, BoxExtent);

    // Filter out tiny props or particles
    if (BoxExtent.X < 20.0f && BoxExtent.Y < 20.0f && BoxExtent.Z < 20.0f)
    {
        return false;
    }

    // 2. Convert centimeters to real-world meters
    float LengthMeters = (BoxExtent.Y * 2.0f) / 100.0f;
    float WidthMeters = (BoxExtent.X * 2.0f) / 100.0f;
    float HeightMeters = (BoxExtent.Z * 2.0f) / 100.0f;
    float FootprintArea = LengthMeters * WidthMeters;

    // 3. Identification & Classification
    FString Label = TargetActor->GetActorLabel();
    FString StructId = TEXT("STR-") + FString::FromInt(TargetActor->GetUniqueID() % 1000);
    for (const FName& Tag : TargetActor->Tags)
    {
        FString TagStr = Tag.ToString();
        if (TagStr.StartsWith(TEXT("BLD-")) || TagStr.StartsWith(TEXT("BRG-")) || 
            TagStr.StartsWith(TEXT("BNK-")) || TagStr.StartsWith(TEXT("TWR-")) || TagStr.StartsWith(TEXT("WAL-")))
        {
            StructId = TagStr;
            break;
        }
    }

    FString StructType = TEXT("Tactical Structure");
    if (Label.Contains(TEXT("Bridge")) || StructId.StartsWith(TEXT("BRG"))) StructType = TEXT("Concrete Bridge Span");
    else if (Label.Contains(TEXT("Bunker")) || StructId.StartsWith(TEXT("BNK"))) StructType = TEXT("Fortified Roadblock");
    else if (Label.Contains(TEXT("Tower")) || StructId.StartsWith(TEXT("TWR"))) StructType = TEXT("Elevated Watchtower");
    else if (Label.Contains(TEXT("Wall")) || StructId.StartsWith(TEXT("WAL"))) StructType = TEXT("Masonry Barrier");
    else if (HeightMeters > 5.0f) StructType = TEXT("Multi-Story Facility");
    else StructType = TEXT("Reinforced Concrete Building");

    // 4. Measure Underpass Clearance if bridge / overhang
    float Clearance = 0.0f;
    bool bIsUnderpass = false;
    if (StructType.Contains(TEXT("Bridge")))
    {
        Clearance = MeasureUnderpassClearance(TargetActor, Origin);
        bIsUnderpass = (Clearance > 1.5f);
    }

    // 5. Populate Output Data
    OutInfo.StructureId = StructId;
    OutInfo.StructureName = Label;
    OutInfo.StructureType = StructType;
    OutInfo.WorldLocation = Origin;
    OutInfo.LengthMeters = LengthMeters;
    OutInfo.WidthMeters = WidthMeters;
    OutInfo.HeightMeters = HeightMeters;
    OutInfo.FootprintAreaSqM = FootprintArea;
    OutInfo.Sector = DetermineSector(Origin);
    OutInfo.ClearanceMeters = Clearance;
    OutInfo.bIsUnderpass = bIsUnderpass;
    OutInfo.bIsActive = true;

    CurrentSurvey = OutInfo;
    bHasSurveyTarget = true;

    // 6. Draw 3D Tactical Corner Brackets & Dimension Annotation in World
    if (bDrawDebugReticles)
    {
        DrawTacticalCornerBrackets(Origin, BoxExtent, ReticleColor);
    }

    if (LastSurveyedActor != TargetActor)
    {
        LastSurveyedActor = TargetActor;
        OnStructureSurveyChanged.Broadcast(CurrentSurvey);
    }

    return true;
}

void UTacticalStructureSurveyor::ClearSurvey()
{
    bHasSurveyTarget = false;
    LastSurveyedActor = nullptr;
    CurrentSurvey = FStructureSurveyInfo();
    OnStructureSurveyChanged.Broadcast(CurrentSurvey);
}

FString UTacticalStructureSurveyor::DetermineSector(const FVector& WorldLocationCm) const
{
    float XM = WorldLocationCm.X / 100.0f;
    float YM = WorldLocationCm.Y / 100.0f;

    if (FMath::Abs(XM) <= 15.0f && FMath::Abs(YM) <= 15.0f) return TEXT("Central Town Square");
    if (XM < 0 && YM >= 0) return TEXT("Sector NW");
    if (XM >= 0 && YM >= 0) return TEXT("Sector NE");
    if (XM < 0 && YM < 0) return TEXT("Sector SW");
    return TEXT("Sector SE");
}

float UTacticalStructureSurveyor::MeasureUnderpassClearance(AActor* BridgeActor, const FVector& SurfaceLocation) const
{
    if (!GetWorld() || !BridgeActor) return 0.0f;

    FVector Origin, Extent;
    BridgeActor->GetActorBounds(false, Origin, Extent);

    FVector Underside = Origin - FVector(0, 0, Extent.Z);
    FVector GroundTraceEnd = Underside - FVector(0, 0, 1500.0f); // 15 meters down

    FCollisionQueryParams Params(FName(TEXT("UnderpassTrace")), true, BridgeActor);
    FHitResult GroundHit;
    if (GetWorld()->LineTraceSingleByChannel(GroundHit, Underside, GroundTraceEnd, ECC_Visibility, Params))
    {
        float DistCm = (Underside.Z - GroundHit.ImpactPoint.Z);
        return FMath::Max(0.0f, DistCm / 100.0f);
    }

    return 0.0f;
}

void UTacticalStructureSurveyor::DrawTacticalCornerBrackets(const FVector& Origin, const FVector& BoxExtent, const FColor& Color) const
{
    if (!GetWorld()) return;

    // Draw tactical bounding box outline
    DrawDebugBox(GetWorld(), Origin, BoxExtent, FQuat::Identity, Color, false, 0.05f, 0, 2.0f);

    // Floating Tactical HUD Banner above top of building
    FVector BannerLoc = Origin + FVector(0, 0, BoxExtent.Z + 60.0f);
    FString BannerText = FString::Printf(TEXT("[%s] %s\nL: %.1fm  W: %.1fm  H: %.1fm  |  Area: %.0fm²"),
        *CurrentSurvey.StructureId,
        *CurrentSurvey.StructureName,
        CurrentSurvey.LengthMeters,
        CurrentSurvey.WidthMeters,
        CurrentSurvey.HeightMeters,
        CurrentSurvey.FootprintAreaSqM
    );

    if (CurrentSurvey.bIsUnderpass)
    {
        BannerText += FString::Printf(TEXT("\n[UNDERPASS CLEARANCE: %.1fm (TRAVERSABLE)]"), CurrentSurvey.ClearanceMeters);
    }

    DrawDebugString(GetWorld(), BannerLoc, BannerText, nullptr, FColor::White, 0.05f, true, 1.25f);
}
