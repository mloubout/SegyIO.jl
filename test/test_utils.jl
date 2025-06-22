using SegyIO
using Distributed
using Test

@testset "Utility Functions" begin
    @testset "delim_vector" begin
        x = [1,1,1,2,2,2,3,3]
        @test delim_vector(x,1) == [1,4,7]
        @test delim_vector(x,2) == [1,4,7]
    end

    @testset "find_next_delim" begin
        x = [1,1,1,2,2,3]
        @test find_next_delim(x,1,1) == 4
        @test find_next_delim(x,4,1) == 6
        @test find_next_delim([1,1,1],1,1) == 3
    end

    @testset "ordered_pmap" begin
        addprocs(1)
        res = ordered_pmap(y->y^2, 1:4)
        rmprocs(workers())
        @test res == [1,4,9,16]
    end

    @testset "get_header scaling" begin
        b = SeisBlock(rand(Float32,10,5))
        set_header!(b, :SourceX, 10)
        set_header!(b, :RecSourceScalar, 2)
        @test get_header(b, :SourceX, scale=false) == fill(Int32(10),5)
        @test get_header(b, :SourceX) == fill(20.0,5)
    end

    @testset "split and merge" begin
        b = SeisBlock(rand(Float32,10,10))
        part = split(b, 1:4)
        @test size(part) == (10,4)
        other = split(b, 5:8)
        merged = merge([part, other])
        @test size(merged) == (10,8)
    end

    @testset "scan_file" begin
        file = joinpath(SegyIO.myRoot, "data/overthrust_2D_shot_1_20.segy")
        s = scan_file(file, ["SourceX","SourceY"], 300, chunksize=1, verbosity=0)
        @test s.ns == 751
        @test length(s) > 0
    end
end
