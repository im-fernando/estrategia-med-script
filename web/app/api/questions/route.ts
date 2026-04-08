import { NextRequest, NextResponse } from "next/server";
import { fetchQuestions } from "@/lib/queries";
import type { Filters } from "@/lib/types";

export async function GET(request: NextRequest) {
  const sp = request.nextUrl.searchParams;

  const filters: Filters = {
    page: Number(sp.get("page")) || 1,
    search: sp.get("search") || undefined,
    specialties: sp.get("specialties")?.split(",").filter(Boolean) || undefined,
    institutions: sp.get("institutions")?.split(",").filter(Boolean) || undefined,
    years: sp.get("years")?.split(",").map(Number).filter(Boolean) || undefined,
    finalidades: sp.get("finalidades")?.split(",").filter(Boolean) || undefined,
    bancas: sp.get("bancas")?.split(",").filter(Boolean) || undefined,
    regions: sp.get("regions")?.split(",").filter(Boolean) || undefined,
    types: sp.get("types")?.split(",").filter(Boolean) || undefined,
    showOutdated: sp.get("showOutdated") !== "false",
    showCanceled: sp.get("showCanceled") !== "false",
  };

  try {
    const result = fetchQuestions(filters);
    return NextResponse.json(result);
  } catch (err) {
    return NextResponse.json(
      { error: String(err) },
      { status: 500 }
    );
  }
}
