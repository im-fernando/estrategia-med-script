import { NextResponse } from "next/server";
import { fetchFilterValues } from "@/lib/queries";

export async function GET() {
  try {
    const values = fetchFilterValues();
    return NextResponse.json(values);
  } catch (err) {
    return NextResponse.json(
      { error: String(err) },
      { status: 500 }
    );
  }
}
